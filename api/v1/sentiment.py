from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from modules.sentiment import sentiment_engine
from core.llm import llm_router, get_ollama

router = APIRouter()

# Wire up the sentiment engine with LLM providers
sentiment_engine.set_llm_router(llm_router)
sentiment_engine.set_ollama_client(get_ollama())


class SentimentRequest(BaseModel):
    text: str
    language: Optional[str] = "en"
    include_emotions: Optional[bool] = False
    include_entities: Optional[bool] = False
    aspects: Optional[List[str]] = None
    use_llm: Optional[bool] = True


class SentimentScoreModel(BaseModel):
    label: str
    confidence: float
    scores: Dict[str, float] = {}


class EmotionScoreModel(BaseModel):
    primary_emotion: str
    confidence: float
    emotions: Dict[str, float] = {}


class EntitySentimentModel(BaseModel):
    entity: str
    entity_type: str
    sentiment: SentimentScoreModel
    mentions: int = 1
    context: str = ""


class SentimentResult(BaseModel):
    text: str
    sentiment: SentimentScoreModel
    emotions: Optional[EmotionScoreModel] = None
    entities: List[EntitySentimentModel] = []
    aspects: Dict[str, SentimentScoreModel] = {}
    metadata: Dict[str, Any] = {}


@router.post("/analyze", response_model=SentimentResult)
async def analyze_sentiment(request: SentimentRequest):
    """
    Analyze sentiment of the provided text.
    """
    result = await sentiment_engine.analyze(
        text=request.text,
        include_emotions=request.include_emotions,
        include_entities=request.include_entities,
        aspects=request.aspects,
        use_llm=request.use_llm
    )
    
    response = SentimentResult(
        text=result.text,
        sentiment=SentimentScoreModel(
            label=result.sentiment.label.value,
            confidence=result.sentiment.confidence,
            scores=result.sentiment.scores
        ),
        metadata=result.metadata
    )
    
    if result.emotions:
        response.emotions = EmotionScoreModel(
            primary_emotion=result.emotions.primary_emotion.value,
            confidence=result.emotions.confidence,
            emotions=result.emotions.emotions
        )
    
    if result.entities:
        response.entities = [
            EntitySentimentModel(
                entity=e.entity,
                entity_type=e.entity_type,
                sentiment=SentimentScoreModel(
                    label=e.sentiment.label.value,
                    confidence=e.sentiment.confidence,
                    scores=e.sentiment.scores
                ),
                mentions=e.mentions,
                context=e.context
            )
            for e in result.entities
        ]
    
    if result.aspects:
        response.aspects = {
            aspect: SentimentScoreModel(
                label=score.label.value,
                confidence=score.confidence,
                scores=score.scores
            )
            for aspect, score in result.aspects.items()
        }
    
    return response


class BatchSentimentRequest(BaseModel):
    texts: List[str]
    use_llm: Optional[bool] = False  # Default to lexicon for batch


@router.post("/batch")
async def batch_sentiment(request: BatchSentimentRequest):
    """
    Analyze sentiment for multiple texts.
    """
    results = await sentiment_engine.batch_analyze(
        texts=request.texts,
        use_llm=request.use_llm
    )
    
    return {
        "count": len(results),
        "results": [
            {
                "text": r.text[:100] + "..." if len(r.text) > 100 else r.text,
                "sentiment": r.sentiment.label.value,
                "confidence": r.sentiment.confidence,
                "scores": r.sentiment.scores
            }
            for r in results
        ],
        "summary": {
            "positive": len([r for r in results if "positive" in r.sentiment.label.value]),
            "negative": len([r for r in results if "negative" in r.sentiment.label.value]),
            "neutral": len([r for r in results if r.sentiment.label.value == "neutral"])
        }
    }


class EntityAnalysisRequest(BaseModel):
    text: str


@router.post("/entities")
async def extract_entities_sentiment(request: EntityAnalysisRequest):
    """
    Extract named entities and their sentiment.
    """
    result = await sentiment_engine.analyze(
        text=request.text,
        include_entities=True,
        use_llm=True
    )
    
    return {
        "text": result.text,
        "overall_sentiment": result.sentiment.label.value,
        "entities": [
            {
                "entity": e.entity,
                "type": e.entity_type,
                "sentiment": e.sentiment.label.value,
                "confidence": e.sentiment.confidence,
                "context": e.context
            }
            for e in result.entities
        ]
    }


class EmotionAnalysisRequest(BaseModel):
    text: str


@router.post("/emotions")
async def analyze_emotions(request: EmotionAnalysisRequest):
    """
    Analyze emotions in text.
    """
    result = await sentiment_engine.analyze(
        text=request.text,
        include_emotions=True,
        use_llm=True
    )
    
    response = {
        "text": result.text,
        "sentiment": result.sentiment.label.value
    }
    
    if result.emotions:
        response["primary_emotion"] = result.emotions.primary_emotion.value
        response["emotion_confidence"] = result.emotions.confidence
        response["emotion_scores"] = result.emotions.emotions
    
    return response


class CompareRequest(BaseModel):
    text1: str
    text2: str


@router.post("/compare")
async def compare_sentiment(request: CompareRequest):
    """
    Compare sentiment between two texts.
    """
    comparison = await sentiment_engine.compare_sentiment(
        text1=request.text1,
        text2=request.text2
    )
    
    return comparison


class AspectAnalysisRequest(BaseModel):
    text: str
    aspects: List[str]


@router.post("/aspects")
async def analyze_aspects(request: AspectAnalysisRequest):
    """
    Analyze sentiment for specific aspects.
    """
    result = await sentiment_engine.analyze(
        text=request.text,
        aspects=request.aspects,
        use_llm=True
    )
    
    return {
        "text": result.text[:200] + "..." if len(result.text) > 200 else result.text,
        "overall_sentiment": result.sentiment.label.value,
        "aspects": {
            aspect: {
                "sentiment": score.label.value,
                "confidence": score.confidence
            }
            for aspect, score in result.aspects.items()
        }
    }
