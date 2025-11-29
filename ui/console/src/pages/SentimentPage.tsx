import { useState, useEffect } from 'react';
import { Sparkles, ThumbsUp, ThumbsDown, Minus, Heart, Frown, Angry, AlertTriangle, Cpu, Cloud, ChevronDown, Clock } from 'lucide-react';
import { sentimentApi, llmApi } from '../api/client';

interface SentimentResult {
  sentiment: {
    label: string;
    confidence: number;
    scores: { positive: number; negative: number; neutral: number };
  };
  emotions?: {
    primary_emotion: string;
    confidence: number;
    emotion_scores: Record<string, number>;
  };
  metadata?: {
    llm_used: boolean;
    timings_ms?: Record<string, number>;
    total_ms?: number;
  };
}

interface ModelOption {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic' | 'ollama';
  available: boolean;
}

export default function SentimentPage() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SentimentResult | null>(null);
  
  // Model selection
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-4o-mini');
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await llmApi.getProviders();
      const providers = response.data.providers;
      const modelList: ModelOption[] = [];
      
      if (providers.ollama?.available) {
        providers.ollama.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'ollama', available: true });
        });
      }
      if (providers.openai?.available) {
        providers.openai.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'openai', available: true });
        });
      }
      if (providers.anthropic?.available) {
        providers.anthropic.models.forEach((m: string) => {
          modelList.push({ id: m, name: m, provider: 'anthropic', available: true });
        });
      }
      
      setModels(modelList);
      if (modelList.length > 0) setSelectedModel(modelList[0].id);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  const getProviderIcon = (provider: string) => {
    if (provider === 'ollama') return <Cpu size={14} />;
    return <Cloud size={14} />;
  };
  
  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'ollama': return '#10b981';
      case 'openai': return '#00d4ff';
      case 'anthropic': return '#d97706';
      default: return 'var(--text-muted)';
    }
  };
  
  const currentModel = models.find(m => m.id === selectedModel);

  const analyzeSentiment = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await sentimentApi.analyze(text, { 
        use_llm: true, 
        include_emotions: true,
        model: selectedModel 
      });
      
      // Also get emotions
      let emotions = null;
      try {
        const emotionResponse = await sentimentApi.emotions(text);
        emotions = {
          primary_emotion: emotionResponse.data.primary_emotion,
          confidence: emotionResponse.data.emotion_confidence,
          emotion_scores: emotionResponse.data.emotion_scores || {}
        };
      } catch (e) {
        console.error('Emotion analysis failed:', e);
      }
      
      setResult({
        sentiment: response.data.sentiment,
        emotions,
        metadata: response.data.metadata
      });
    } catch (error) {
      console.error('Failed to analyze:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSentimentIcon = (label: string) => {
    if (label.includes('positive')) return <ThumbsUp size={32} />;
    if (label.includes('negative')) return <ThumbsDown size={32} />;
    return <Minus size={32} />;
  };

  const getSentimentColor = (label: string) => {
    if (label.includes('positive')) return 'var(--accent-tertiary)';
    if (label.includes('negative')) return 'var(--accent-danger)';
    return 'var(--text-muted)';
  };

  const getEmotionIcon = (emotion: string) => {
    switch (emotion.toLowerCase()) {
      case 'joy': return <Heart size={20} />;
      case 'sadness': return <Frown size={20} />;
      case 'anger': return <Angry size={20} />;
      case 'fear': return <AlertTriangle size={20} />;
      default: return <Sparkles size={20} />;
    }
  };

  const sampleTexts = [
    { label: 'Positive', text: 'I absolutely love this product! It exceeded all my expectations and the customer service was amazing.' },
    { label: 'Negative', text: 'This was a terrible experience. The service was slow, the staff was rude, and the product broke after one day.' },
    { label: 'Neutral', text: 'The meeting was held on Tuesday. We discussed the quarterly report and next steps for the project.' },
    { label: 'Mixed', text: 'The food was delicious but the wait time was unacceptable. Great flavors, poor service.' }
  ];

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="page-title">Sentiment Analysis</h1>
            <p className="page-subtitle">Analyze emotions and sentiment in text</p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {/* Model Selector */}
            <div style={{ position: 'relative' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowModelDropdown(!showModelDropdown)}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 160 }}
                >
                  <span style={{ color: getProviderColor(currentModel?.provider || 'openai') }}>
                    {getProviderIcon(currentModel?.provider || 'openai')}
                  </span>
                  <span style={{ flex: 1, textAlign: 'left' }}>{selectedModel}</span>
                  <ChevronDown size={14} />
                </button>
                
                {showModelDropdown && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: 4,
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    padding: 8,
                    minWidth: 200,
                    zIndex: 100,
                    boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
                  }}>
                    {['ollama', 'openai', 'anthropic'].map(provider => {
                      const providerModels = models.filter(m => m.provider === provider);
                      if (providerModels.length === 0) return null;
                      
                      return (
                        <div key={provider}>
                          <div style={{
                            fontSize: 10,
                            color: getProviderColor(provider),
                            padding: '8px 8px 4px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            textTransform: 'uppercase'
                          }}>
                            {getProviderIcon(provider)}
                            {provider}
                            {provider === 'ollama' && <span style={{ 
                              fontSize: 9, 
                              background: 'rgba(16, 185, 129, 0.2)',
                              padding: '2px 6px',
                              borderRadius: 4
                            }}>LOCAL</span>}
                          </div>
                          {providerModels.map(model => (
                            <button
                              key={model.id}
                              onClick={() => {
                                setSelectedModel(model.id);
                                setShowModelDropdown(false);
                              }}
                              style={{
                                display: 'block',
                                width: '100%',
                                padding: '8px 12px',
                                textAlign: 'left',
                                background: model.id === selectedModel ? 'var(--bg-hover)' : 'transparent',
                                border: 'none',
                                borderRadius: 'var(--radius-sm)',
                                color: 'var(--text-primary)',
                                cursor: 'pointer',
                                fontSize: 13
                              }}
                            >
                              {model.name}
                            </button>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
          </div>
        </div>
      </header>

      <div className="page-content">
        <div className="grid-2">
          {/* Input */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Sparkles size={20} style={{ marginRight: 8 }} />
                Analyze Text
              </h2>
            </div>

            <div style={{ marginBottom: 16 }}>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter text to analyze sentiment and emotions..."
                style={{ minHeight: 150 }}
              />
            </div>

            <button
              className="btn btn-primary"
              onClick={analyzeSentiment}
              disabled={loading || !text.trim()}
              style={{ width: '100%' }}
            >
              {loading ? (
                <>
                  <div className="spinner" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Analyze Sentiment
                </>
              )}
            </button>

            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 12, color: 'var(--text-secondary)' }}>
                Try these samples:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {sampleTexts.map((sample, i) => (
                  <div
                    key={i}
                    onClick={() => setText(sample.text)}
                    style={{
                      padding: 12,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--accent-primary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'transparent';
                    }}
                  >
                    <span className={`tag ${sample.label === 'Positive' ? 'success' : sample.label === 'Negative' ? 'error' : 'info'}`} style={{ marginBottom: 8 }}>
                      {sample.label}
                    </span>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 6 }}>
                      {sample.text.slice(0, 80)}...
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Results */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Analysis Results</h2>
            </div>

            {result ? (
              <div>
                {/* Main Sentiment */}
                <div
                  style={{
                    padding: 24,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-lg)',
                    marginBottom: 20,
                    textAlign: 'center'
                  }}
                >
                  <div
                    style={{
                      width: 80,
                      height: 80,
                      borderRadius: '50%',
                      background: `${getSentimentColor(result.sentiment.label)}20`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px',
                      color: getSentimentColor(result.sentiment.label)
                    }}
                  >
                    {getSentimentIcon(result.sentiment.label)}
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 700, textTransform: 'capitalize', marginBottom: 8 }}>
                    {result.sentiment.label.replace('_', ' ')}
                  </div>
                  <div style={{ color: 'var(--text-secondary)' }}>
                    Confidence: {(result.sentiment.confidence * 100).toFixed(0)}%
                  </div>
                  {result.metadata && (
                    <div style={{ 
                      marginTop: 12, 
                      padding: '8px 16px',
                      background: 'var(--bg-primary)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: 13, 
                      display: 'flex',
                      gap: 16,
                      justifyContent: 'center',
                      alignItems: 'center'
                    }}>
                      <span style={{ color: getProviderColor(currentModel?.provider || 'openai'), display: 'flex', alignItems: 'center', gap: 6 }}>
                        {getProviderIcon(currentModel?.provider || 'openai')}
                        {selectedModel}
                      </span>
                      {result.metadata.total_ms !== undefined && (
                        <span style={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: 6,
                          color: result.metadata.total_ms < 1000 ? '#10b981' : 'var(--text-muted)'
                        }}>
                          <Clock size={14} />
                          {result.metadata.total_ms > 1000 
                            ? `${(result.metadata.total_ms / 1000).toFixed(1)}s` 
                            : `${Math.round(result.metadata.total_ms)}ms`}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Score Bars */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 12 }}>Sentiment Scores</div>
                  {['positive', 'neutral', 'negative'].map((key) => {
                    const value = result.sentiment.scores[key as keyof typeof result.sentiment.scores] || 0;
                    const colors = {
                      positive: 'var(--accent-tertiary)',
                      neutral: 'var(--text-muted)',
                      negative: 'var(--accent-danger)'
                    };
                    return (
                      <div key={key} style={{ marginBottom: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13 }}>
                          <span style={{ textTransform: 'capitalize' }}>{key}</span>
                          <span>{(value * 100).toFixed(0)}%</span>
                        </div>
                        <div style={{ height: 8, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden' }}>
                          <div
                            style={{
                              height: '100%',
                              width: `${value * 100}%`,
                              background: colors[key as keyof typeof colors],
                              borderRadius: 4,
                              transition: 'width 0.5s ease'
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Emotions */}
                {result.emotions && (
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 12 }}>Primary Emotion</div>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: 16,
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)'
                      }}
                    >
                      <div
                        style={{
                          width: 40,
                          height: 40,
                          borderRadius: 'var(--radius-md)',
                          background: 'rgba(124, 58, 237, 0.15)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'var(--accent-secondary)'
                        }}
                      >
                        {getEmotionIcon(result.emotions.primary_emotion)}
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                          {result.emotions.primary_emotion}
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                          Confidence: {(result.emotions.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>

                    {Object.keys(result.emotions.emotion_scores).length > 0 && (
                      <div style={{ marginTop: 16 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8, color: 'var(--text-secondary)' }}>
                          All Emotions
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                          {Object.entries(result.emotions.emotion_scores)
                            .filter(([, score]) => score > 0)
                            .sort(([, a], [, b]) => b - a)
                            .map(([emotion, score]) => (
                              <span
                                key={emotion}
                                className="tag"
                                style={{
                                  background: `rgba(124, 58, 237, ${score})`,
                                  color: score > 0.5 ? 'white' : 'var(--text-primary)'
                                }}
                              >
                                {emotion}: {(score * 100).toFixed(0)}%
                              </span>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 60,
                  color: 'var(--text-muted)',
                  textAlign: 'center'
                }}
              >
                <Sparkles size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
                <div>Enter text to analyze sentiment and emotions</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

