import { useState } from 'react'
import {
  Brain,
  Play,
  Hash,
  Users,
  DollarSign,
  Percent,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts'
import {
  useRunNLPAnalysis,
  useTopicSummary,
  useMarketSentiment,
} from '../hooks/useApi'
import * as api from '../services/api'

export default function NLPAnalysis() {
  const [text, setText] = useState('')
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [entityResult, setEntityResult] = useState<any>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const nlpMutation = useRunNLPAnalysis()
  const { data: topics, isLoading: topicsLoading } = useTopicSummary()
  const { data: marketSentiment, isLoading: marketLoading } = useMarketSentiment(7, 100)

  const handleAnalyzeText = async () => {
    if (!text.trim()) return
    setIsAnalyzing(true)
    try {
      const [sentiment, entities] = await Promise.all([
        api.analyzeSentiment(text),
        api.extractEntities(text),
      ])
      setAnalysisResult(sentiment)
      setEntityResult(entities)
    } catch (error) {
      console.error('Analysis failed:', error)
    }
    setIsAnalyzing(false)
  }

  const handleRunPipeline = () => {
    nlpMutation.mutate({ limit: 50, fitTopics: true })
  }

  const sentimentColor = (score: number) => {
    if (score > 0.1) return '#10b981'
    if (score < -0.1) return '#ef4444'
    return '#6b7280'
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
            <Brain className="w-8 h-8 mr-3 text-purple-600" />
            NLP Analysis
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            FinBERT sentiment, entity extraction, and topic modeling
          </p>
        </div>
        <button
          onClick={handleRunPipeline}
          disabled={nlpMutation.isPending}
          className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          <Play className={`w-4 h-4 mr-2 ${nlpMutation.isPending ? 'animate-pulse' : ''}`} />
          {nlpMutation.isPending ? 'Running...' : 'Run Full Pipeline'}
        </button>
      </div>

      {/* Pipeline Result */}
      {nlpMutation.isSuccess && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <p className="text-green-800 dark:text-green-200">
            Processed {nlpMutation.data.processed} articles, stored {nlpMutation.data.stored},
            updated {nlpMutation.data.ticker_updates} ticker mentions.
            {nlpMutation.data.topics_fitted && ' Topics fitted!'}
          </p>
        </div>
      )}

      {/* Market Sentiment Card */}
      {marketSentiment && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Market Sentiment (FinBERT Analysis)
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-500">Articles Analyzed</p>
              <p className="text-2xl font-bold">{marketSentiment.total_articles}</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-500">Avg Sentiment</p>
              <p
                className="text-2xl font-bold"
                style={{ color: sentimentColor(marketSentiment.average_sentiment) }}
              >
                {(marketSentiment.average_sentiment * 100).toFixed(1)}%
              </p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-500">Confidence</p>
              <p className="text-2xl font-bold">{(marketSentiment.confidence * 100).toFixed(0)}%</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-500">Market Mood</p>
              <p className="text-2xl font-bold capitalize flex items-center justify-center">
                {marketSentiment.market_mood === 'bullish' && (
                  <TrendingUp className="w-6 h-6 text-green-500 mr-1" />
                )}
                {marketSentiment.market_mood === 'bearish' && (
                  <TrendingDown className="w-6 h-6 text-red-500 mr-1" />
                )}
                {marketSentiment.market_mood === 'neutral' && (
                  <Minus className="w-6 h-6 text-gray-500 mr-1" />
                )}
                {marketSentiment.market_mood}
              </p>
            </div>
          </div>

          {/* Sentiment Distribution */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Sentiment Distribution
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Positive', value: marketSentiment.positive_count, color: '#10b981' },
                      { name: 'Negative', value: marketSentiment.negative_count, color: '#ef4444' },
                      { name: 'Neutral', value: marketSentiment.neutral_count, color: '#6b7280' },
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={70}
                    dataKey="value"
                  >
                    {[
                      { color: '#10b981' },
                      { color: '#ef4444' },
                      { color: '#6b7280' },
                    ].map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col justify-center space-y-3">
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <span className="text-green-700 dark:text-green-300">Positive</span>
                <span className="font-bold">
                  {marketSentiment.positive_count} ({(marketSentiment.positive_ratio * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <span className="text-red-700 dark:text-red-300">Negative</span>
                <span className="font-bold">
                  {marketSentiment.negative_count} ({(marketSentiment.negative_ratio * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <span className="text-gray-700 dark:text-gray-300">Neutral</span>
                <span className="font-bold">{marketSentiment.neutral_count}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Topic Summary */}
      {topics && topics.topics && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Discovered Topics (BERTopic)
          </h2>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <p className="text-sm text-gray-500">Total Documents</p>
              <p className="text-xl font-bold">{topics.total_documents}</p>
            </div>
            <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <p className="text-sm text-gray-500">Topics Found</p>
              <p className="text-xl font-bold">{topics.num_topics}</p>
            </div>
            <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-500">Outliers</p>
              <p className="text-xl font-bold">{topics.outliers}</p>
            </div>
          </div>

          <div className="space-y-3">
            {topics.topics.slice(0, 8).map((topic: any) => (
              <div
                key={topic.id}
                className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900 dark:text-white">
                    Topic {topic.id}: {topic.name}
                  </span>
                  <span className="text-sm text-gray-500">
                    {topic.count} articles ({topic.percentage}%)
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {topic.keywords.slice(0, 6).map((kw: string, i: number) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interactive Text Analysis */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Analyze Custom Text
        </h2>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter financial news text to analyze sentiment and extract entities..."
          className="w-full h-32 p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
        <button
          onClick={handleAnalyzeText}
          disabled={isAnalyzing || !text.trim()}
          className="mt-4 flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          <Brain className={`w-4 h-4 mr-2 ${isAnalyzing ? 'animate-pulse' : ''}`} />
          {isAnalyzing ? 'Analyzing...' : 'Analyze'}
        </button>

        {/* Analysis Results */}
        {analysisResult && (
          <div className="mt-6 space-y-4">
            {/* Overall Sentiment */}
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <h3 className="font-medium mb-2">Overall Sentiment (FinBERT)</h3>
              <div className="flex items-center gap-4">
                <span
                  className="text-2xl font-bold"
                  style={{ color: sentimentColor(analysisResult.overall.score) }}
                >
                  {analysisResult.overall.label.toUpperCase()}
                </span>
                <span className="text-gray-500">
                  Score: {(analysisResult.overall.score * 100).toFixed(1)}%
                </span>
                <span className="text-gray-500">
                  Confidence: {(analysisResult.overall.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Sentence Breakdown */}
            {analysisResult.sentences.length > 0 && (
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <h3 className="font-medium mb-3">Sentence-Level Analysis</h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {analysisResult.sentences.map((s: any, i: number) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 p-2 bg-white dark:bg-gray-900 rounded"
                    >
                      <span
                        className="px-2 py-0.5 text-xs font-medium rounded"
                        style={{
                          backgroundColor: sentimentColor(s.score) + '20',
                          color: sentimentColor(s.score),
                        }}
                      >
                        {s.label}
                      </span>
                      <span className="text-sm text-gray-700 dark:text-gray-300">{s.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Entity Results */}
        {entityResult && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Tickers */}
            {entityResult.tickers.length > 0 && (
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <h3 className="font-medium mb-2 flex items-center">
                  <Hash className="w-4 h-4 mr-1" /> Tickers Found
                </h3>
                <div className="flex flex-wrap gap-2">
                  {entityResult.tickers.map((t: any, i: number) => (
                    <span
                      key={i}
                      className="px-2 py-1 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200 rounded"
                    >
                      ${t.symbol}
                      {t.company_name && (
                        <span className="text-xs ml-1 opacity-70">({t.company_name})</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* People */}
            {entityResult.people.length > 0 && (
              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <h3 className="font-medium mb-2 flex items-center">
                  <Users className="w-4 h-4 mr-1" /> People Mentioned
                </h3>
                <div className="space-y-1">
                  {entityResult.people.map((p: any, i: number) => (
                    <div key={i} className="text-sm">
                      <span className="font-medium">{p.name}</span>
                      {p.title && <span className="text-gray-500 ml-1">({p.title})</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Money */}
            {entityResult.metrics.monetary.length > 0 && (
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <h3 className="font-medium mb-2 flex items-center">
                  <DollarSign className="w-4 h-4 mr-1" /> Monetary Values
                </h3>
                <div className="space-y-1">
                  {entityResult.metrics.monetary.map((m: any, i: number) => (
                    <div key={i} className="text-sm font-mono">
                      {m.value}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Percentages */}
            {entityResult.metrics.percentages.length > 0 && (
              <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <h3 className="font-medium mb-2 flex items-center">
                  <Percent className="w-4 h-4 mr-1" /> Percentages
                </h3>
                <div className="space-y-1">
                  {entityResult.metrics.percentages.map((p: any, i: number) => (
                    <div key={i} className="text-sm font-mono">
                      {p.value}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
