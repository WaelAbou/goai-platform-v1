"""
Sentiment Analysis Engine - Text sentiment and emotion analysis.
Supports multiple analysis modes and entity-level sentiment.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from core.telemetry import tracer, SpanStatus, logger
from core.cache import cache


class SentimentLabel(Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class EmotionLabel(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


@dataclass
class SentimentScore:
    label: SentimentLabel
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class EmotionScore:
    primary_emotion: EmotionLabel
    confidence: float
    emotions: Dict[str, float] = field(default_factory=dict)


@dataclass
class EntitySentiment:
    entity: str
    entity_type: str  # PERSON, ORG, PRODUCT, etc.
    sentiment: SentimentScore
    mentions: int = 1
    context: str = ""


@dataclass
class SentimentResult:
    text: str
    sentiment: SentimentScore
    emotions: Optional[EmotionScore] = None
    entities: List[EntitySentiment] = field(default_factory=list)
    aspects: Dict[str, SentimentScore] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SentimentEngine:
    """
    Sentiment analysis engine with LLM and rule-based capabilities.
    """

    SENTIMENT_PROMPT = """Analyze the sentiment of the following text:

Text: "{text}"

Provide your analysis in this exact format:
SENTIMENT: [very_negative/negative/neutral/positive/very_positive]
CONFIDENCE: [0.0 to 1.0]
POSITIVE_SCORE: [0.0 to 1.0]
NEGATIVE_SCORE: [0.0 to 1.0]
NEUTRAL_SCORE: [0.0 to 1.0]
REASONING: [brief explanation]"""

    EMOTION_PROMPT = """Analyze the emotions expressed in the following text:

Text: "{text}"

Identify the primary emotion and provide scores for each:
PRIMARY_EMOTION: [joy/sadness/anger/fear/surprise/disgust/trust/anticipation/neutral]
CONFIDENCE: [0.0 to 1.0]

Emotion scores (0.0 to 1.0):
JOY: [score]
SADNESS: [score]
ANGER: [score]
FEAR: [score]
SURPRISE: [score]
DISGUST: [score]
TRUST: [score]
ANTICIPATION: [score]"""

    ENTITY_SENTIMENT_PROMPT = """Analyze the sentiment toward specific entities mentioned in this text:

Text: "{text}"

For each entity (person, organization, product, etc.) mentioned:
1. Identify the entity and its type
2. Determine the sentiment expressed toward it
3. Note the context

Format each entity as:
ENTITY: [name] | TYPE: [type] | SENTIMENT: [positive/negative/neutral] | CONTEXT: [brief context]

List all entities found:"""

    ASPECT_SENTIMENT_PROMPT = """Analyze the sentiment for different aspects mentioned in this text:

Text: "{text}"
Aspects to analyze: {aspects}

For each aspect, provide:
ASPECT: [name] | SENTIMENT: [positive/negative/neutral] | CONFIDENCE: [0-1] | EVIDENCE: [text excerpt]

Analyze each aspect:"""

    # Simple lexicon for rule-based fallback
    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic", "love",
        "happy", "joy", "pleased", "satisfied", "beautiful", "perfect", "best",
        "awesome", "brilliant", "outstanding", "superb", "delightful", "positive"
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "horrible", "hate", "angry", "sad", "poor",
        "worst", "disappointing", "frustrated", "annoying", "ugly", "wrong",
        "negative", "unhappy", "upset", "angry", "fail", "failure", "problem"
    }

    INTENSIFIERS = {"very", "extremely", "really", "absolutely", "totally", "completely"}
    NEGATORS = {"not", "no", "never", "neither", "nobody", "nothing", "nowhere"}

    def __init__(self):
        self.llm_router = None
        self.ollama_client = None
        self.prefer_local = True  # Prefer Ollama if available

    def set_llm_router(self, router):
        """Set the LLM router for advanced analysis"""
        self.llm_router = router
    
    def set_ollama_client(self, client):
        """Set Ollama client for local inference"""
        self.ollama_client = client

    def _lexicon_sentiment(self, text: str) -> SentimentScore:
        """Simple lexicon-based sentiment analysis"""
        words = text.lower().split()
        
        positive_count = 0
        negative_count = 0
        intensifier_active = False
        negator_active = False
        
        for i, word in enumerate(words):
            # Check for intensifiers and negators
            if word in self.INTENSIFIERS:
                intensifier_active = True
                continue
            if word in self.NEGATORS:
                negator_active = True
                continue
            
            # Calculate sentiment
            multiplier = 1.5 if intensifier_active else 1.0
            
            if word in self.POSITIVE_WORDS:
                if negator_active:
                    negative_count += multiplier
                else:
                    positive_count += multiplier
            elif word in self.NEGATIVE_WORDS:
                if negator_active:
                    positive_count += multiplier
                else:
                    negative_count += multiplier
            
            # Reset modifiers after use
            intensifier_active = False
            negator_active = False
        
        total = positive_count + negative_count + 1  # +1 to avoid division by zero
        
        positive_score = positive_count / total
        negative_score = negative_count / total
        neutral_score = 1 - positive_score - negative_score
        
        # Determine label
        if positive_score > 0.6:
            label = SentimentLabel.VERY_POSITIVE if positive_score > 0.8 else SentimentLabel.POSITIVE
        elif negative_score > 0.6:
            label = SentimentLabel.VERY_NEGATIVE if negative_score > 0.8 else SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL
        
        confidence = max(positive_score, negative_score, neutral_score)
        
        return SentimentScore(
            label=label,
            confidence=round(confidence, 2),
            scores={
                "positive": round(positive_score, 2),
                "negative": round(negative_score, 2),
                "neutral": round(neutral_score, 2)
            }
        )

    def _parse_sentiment_response(self, response: str) -> SentimentScore:
        """Parse LLM sentiment response"""
        label = SentimentLabel.NEUTRAL
        confidence = 0.5
        scores = {"positive": 0.33, "negative": 0.33, "neutral": 0.34}
        
        # Parse sentiment label
        label_match = re.search(r'SENTIMENT:\s*(\w+)', response, re.IGNORECASE)
        if label_match:
            label_str = label_match.group(1).lower()
            label_map = {
                "very_negative": SentimentLabel.VERY_NEGATIVE,
                "negative": SentimentLabel.NEGATIVE,
                "neutral": SentimentLabel.NEUTRAL,
                "positive": SentimentLabel.POSITIVE,
                "very_positive": SentimentLabel.VERY_POSITIVE
            }
            label = label_map.get(label_str, SentimentLabel.NEUTRAL)
        
        # Parse confidence
        conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
            except ValueError:
                pass
        
        # Parse individual scores
        for score_type in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            match = re.search(rf'{score_type}_SCORE:\s*([\d.]+)', response, re.IGNORECASE)
            if match:
                try:
                    scores[score_type.lower()] = float(match.group(1))
                except ValueError:
                    pass
        
        return SentimentScore(
            label=label,
            confidence=confidence,
            scores=scores
        )

    def _parse_emotion_response(self, response: str) -> EmotionScore:
        """Parse LLM emotion response"""
        primary = EmotionLabel.NEUTRAL
        confidence = 0.5
        emotions = {}
        
        # Parse primary emotion
        primary_match = re.search(r'PRIMARY_EMOTION:\s*(\w+)', response, re.IGNORECASE)
        if primary_match:
            emotion_str = primary_match.group(1).lower()
            emotion_map = {
                "joy": EmotionLabel.JOY,
                "sadness": EmotionLabel.SADNESS,
                "anger": EmotionLabel.ANGER,
                "fear": EmotionLabel.FEAR,
                "surprise": EmotionLabel.SURPRISE,
                "disgust": EmotionLabel.DISGUST,
                "trust": EmotionLabel.TRUST,
                "anticipation": EmotionLabel.ANTICIPATION,
                "neutral": EmotionLabel.NEUTRAL
            }
            primary = emotion_map.get(emotion_str, EmotionLabel.NEUTRAL)
        
        # Parse confidence
        conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
            except ValueError:
                pass
        
        # Parse emotion scores
        for emotion in ["JOY", "SADNESS", "ANGER", "FEAR", "SURPRISE", "DISGUST", "TRUST", "ANTICIPATION"]:
            match = re.search(rf'{emotion}:\s*([\d.]+)', response, re.IGNORECASE)
            if match:
                try:
                    emotions[emotion.lower()] = float(match.group(1))
                except ValueError:
                    pass
        
        return EmotionScore(
            primary_emotion=primary,
            confidence=confidence,
            emotions=emotions
        )

    async def analyze(
        self,
        text: str,
        include_emotions: bool = False,
        include_entities: bool = False,
        aspects: Optional[List[str]] = None,
        use_llm: bool = True
    ) -> SentimentResult:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            include_emotions: Whether to include emotion analysis
            include_entities: Whether to include entity-level sentiment
            aspects: Specific aspects to analyze sentiment for
            use_llm: Whether to use LLM for analysis
            
        Returns:
            SentimentResult with full analysis
        """
        span = tracer.start_span("sentiment.analyze", attributes={
            "text_length": len(text),
            "use_llm": use_llm,
            "include_emotions": include_emotions,
            "include_entities": include_entities
        })
        
        start_time = time.time()
        timings = {}
        
        try:
            # Use LLM if available and requested
            if use_llm and self.llm_router:
                # Check cache first
                cache_key = f"sentiment:{hash(text[:500])}"
                cached = cache.get(cache_key, "query")
                
                if cached:
                    span.add_event("cache_hit")
                    logger.info("Sentiment cache hit", text_preview=text[:50])
                    sentiment = SentimentScore(
                        label=SentimentLabel(cached["label"]),
                        confidence=cached["confidence"],
                        scores=cached["scores"]
                    )
                    timings["sentiment"] = 0
                else:
                    span.add_event("cache_miss")
                    t0 = time.time()
                    sentiment = await self._llm_sentiment(text)
                    timings["sentiment"] = round((time.time() - t0) * 1000, 2)
                    
                    # Cache the result
                    cache.set(cache_key, {
                        "label": sentiment.label.value,
                        "confidence": sentiment.confidence,
                        "scores": sentiment.scores
                    }, "query", ttl=3600)
                
                if include_emotions:
                    t0 = time.time()
                    emotions = await self._llm_emotions(text)
                    timings["emotions"] = round((time.time() - t0) * 1000, 2)
                else:
                    emotions = None
                
                if include_entities:
                    t0 = time.time()
                    entities = await self._llm_entity_sentiment(text)
                    timings["entities"] = round((time.time() - t0) * 1000, 2)
                else:
                    entities = []
                
                if aspects:
                    t0 = time.time()
                    aspect_sentiments = await self._llm_aspect_sentiment(text, aspects)
                    timings["aspects"] = round((time.time() - t0) * 1000, 2)
                else:
                    aspect_sentiments = {}
            else:
                # Fallback to lexicon-based (fast!)
                t0 = time.time()
                sentiment = self._lexicon_sentiment(text)
                timings["sentiment"] = round((time.time() - t0) * 1000, 2)
                emotions = None
                entities = []
                aspect_sentiments = {}
            
            total_time = round((time.time() - start_time) * 1000, 2)
            span.set_attribute("total_time_ms", total_time)
            span.set_attribute("timings", timings)
            span.set_status(SpanStatus.OK)
            
            logger.info(
                "Sentiment analysis complete",
                total_ms=total_time,
                timings=timings,
                use_llm=use_llm
            )
            
            return SentimentResult(
                text=text[:500] if len(text) > 500 else text,
                sentiment=sentiment,
                emotions=emotions,
                entities=entities,
                aspects=aspect_sentiments,
                metadata={
                    "llm_used": use_llm and self.llm_router is not None,
                    "timings_ms": timings,
                    "total_ms": total_time
                }
            )
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            logger.error("Sentiment analysis failed", error=str(e))
            raise
        finally:
            tracer.end_span(span)

    async def _llm_sentiment(self, text: str) -> SentimentScore:
        """Get sentiment using LLM (prefers Ollama if available)"""
        
        # Try Ollama first if prefer_local is set
        if self.prefer_local and self.ollama_client:
            try:
                if await self.ollama_client.is_available():
                    return await self._ollama_sentiment(text)
            except Exception:
                pass  # Fall through to cloud LLM
        
        if not self.llm_router:
            return self._lexicon_sentiment(text)
        
        span = tracer.start_span("sentiment.llm_call", attributes={
            "model": "gpt-4o-mini",
            "provider": "openai",
            "prompt_length": len(text[:2000])
        })
        
        try:
            prompt = self.SENTIMENT_PROMPT.format(text=text[:2000])
            
            t0 = time.time()
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            llm_time = round((time.time() - t0) * 1000, 2)
            
            span.set_attribute("llm_latency_ms", llm_time)
            span.add_event("llm_response_received", {"latency_ms": llm_time})
            span.set_status(SpanStatus.OK)
            
            return self._parse_sentiment_response(response.get("content", ""))
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            logger.warning("LLM sentiment failed, using lexicon", error=str(e))
            return self._lexicon_sentiment(text)
        finally:
            tracer.end_span(span)
    
    async def _ollama_sentiment(self, text: str) -> SentimentScore:
        """Get sentiment using local Ollama model (fast!)"""
        span = tracer.start_span("sentiment.ollama_call", attributes={
            "model": "llama3.2",
            "provider": "ollama",
            "prompt_length": len(text[:2000])
        })
        
        try:
            prompt = self.SENTIMENT_PROMPT.format(text=text[:2000])
            
            result = await self.ollama_client.generate(
                prompt=prompt,
                model="llama3.2",
                temperature=0,
                max_tokens=200
            )
            
            span.set_attribute("llm_latency_ms", result["latency_ms"])
            span.add_event("ollama_response", {"latency_ms": result["latency_ms"]})
            span.set_status(SpanStatus.OK)
            
            logger.info(
                "Ollama sentiment complete",
                latency_ms=result["latency_ms"],
                model=result["model"]
            )
            
            return self._parse_sentiment_response(result["content"])
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            logger.warning("Ollama sentiment failed", error=str(e))
            raise
        finally:
            tracer.end_span(span)

    async def _llm_emotions(self, text: str) -> EmotionScore:
        """Get emotion analysis using LLM"""
        if not self.llm_router:
            return EmotionScore(
                primary_emotion=EmotionLabel.NEUTRAL,
                confidence=0.5,
                emotions={}
            )
        
        try:
            prompt = self.EMOTION_PROMPT.format(text=text[:2000])
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return self._parse_emotion_response(response.get("content", ""))
        except Exception:
            return EmotionScore(
                primary_emotion=EmotionLabel.NEUTRAL,
                confidence=0.5,
                emotions={}
            )

    async def _llm_entity_sentiment(self, text: str) -> List[EntitySentiment]:
        """Extract entity-level sentiment using LLM"""
        if not self.llm_router:
            return []
        
        try:
            prompt = self.ENTITY_SENTIMENT_PROMPT.format(text=text[:2000])
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            entities = []
            content = response.get("content", "")
            
            # Parse entity lines
            for line in content.split("\n"):
                if "ENTITY:" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        entity_match = re.search(r'ENTITY:\s*([^|]+)', parts[0])
                        type_match = re.search(r'TYPE:\s*(\w+)', parts[1])
                        sent_match = re.search(r'SENTIMENT:\s*(\w+)', parts[2])
                        context = ""
                        if len(parts) > 3:
                            context_match = re.search(r'CONTEXT:\s*(.+)', parts[3])
                            if context_match:
                                context = context_match.group(1).strip()
                        
                        if entity_match and sent_match:
                            sentiment_label = SentimentLabel.NEUTRAL
                            sent_str = sent_match.group(1).lower()
                            if "positive" in sent_str:
                                sentiment_label = SentimentLabel.POSITIVE
                            elif "negative" in sent_str:
                                sentiment_label = SentimentLabel.NEGATIVE
                            
                            entities.append(EntitySentiment(
                                entity=entity_match.group(1).strip(),
                                entity_type=type_match.group(1) if type_match else "UNKNOWN",
                                sentiment=SentimentScore(
                                    label=sentiment_label,
                                    confidence=0.8,
                                    scores={}
                                ),
                                context=context
                            ))
            
            return entities
        except Exception:
            return []

    async def _llm_aspect_sentiment(
        self,
        text: str,
        aspects: List[str]
    ) -> Dict[str, SentimentScore]:
        """Analyze sentiment for specific aspects"""
        if not self.llm_router or not aspects:
            return {}
        
        try:
            prompt = self.ASPECT_SENTIMENT_PROMPT.format(
                text=text[:2000],
                aspects=", ".join(aspects)
            )
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            result = {}
            content = response.get("content", "")
            
            for line in content.split("\n"):
                if "ASPECT:" in line:
                    aspect_match = re.search(r'ASPECT:\s*([^|]+)', line)
                    sent_match = re.search(r'SENTIMENT:\s*(\w+)', line)
                    conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', line)
                    
                    if aspect_match and sent_match:
                        aspect_name = aspect_match.group(1).strip().lower()
                        sentiment_label = SentimentLabel.NEUTRAL
                        sent_str = sent_match.group(1).lower()
                        
                        if "positive" in sent_str:
                            sentiment_label = SentimentLabel.POSITIVE
                        elif "negative" in sent_str:
                            sentiment_label = SentimentLabel.NEGATIVE
                        
                        confidence = 0.7
                        if conf_match:
                            try:
                                confidence = float(conf_match.group(1))
                            except ValueError:
                                pass
                        
                        result[aspect_name] = SentimentScore(
                            label=sentiment_label,
                            confidence=confidence,
                            scores={}
                        )
            
            return result
        except Exception:
            return {}

    async def batch_analyze(
        self,
        texts: List[str],
        **kwargs
    ) -> List[SentimentResult]:
        """Analyze sentiment for multiple texts"""
        results = []
        for text in texts:
            result = await self.analyze(text, **kwargs)
            results.append(result)
        return results

    async def compare_sentiment(
        self,
        text1: str,
        text2: str
    ) -> Dict[str, Any]:
        """Compare sentiment between two texts"""
        result1 = await self.analyze(text1)
        result2 = await self.analyze(text2)
        
        # Calculate difference
        score_diff = (
            result1.sentiment.scores.get("positive", 0) - 
            result2.sentiment.scores.get("positive", 0)
        )
        
        return {
            "text1_sentiment": result1.sentiment.label.value,
            "text2_sentiment": result2.sentiment.label.value,
            "score_difference": round(score_diff, 2),
            "more_positive": "text1" if score_diff > 0 else "text2" if score_diff < 0 else "equal",
            "text1_scores": result1.sentiment.scores,
            "text2_scores": result2.sentiment.scores
        }


# Singleton instance
sentiment_engine = SentimentEngine()

