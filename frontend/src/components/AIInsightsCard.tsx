// AI insights card - shows Claude-generated market analysis on dashboard
import { useState } from 'react'
import {
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Activity,
  Zap,
  AlertCircle,
  Clock,
} from 'lucide-react'
import { useAIInsights, useRefreshAIInsights } from '../hooks/useApi'
import type { TrendAlert } from '../types'

// format date as "5m ago", "2h ago", etc
function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

// icon for trend alert type
function AlertTypeIcon({ type }: { type: TrendAlert['alert_type'] }) {
  switch (type) {
    case 'bullish':
      return <TrendingUp className="w-4 h-4 text-green-500" />
    case 'bearish':
      return <TrendingDown className="w-4 h-4 text-red-500" />
    case 'volatile':
      return <Activity className="w-4 h-4 text-yellow-500" />
    case 'momentum':
      return <Zap className="w-4 h-4 text-blue-500" />
    default:
      return <Activity className="w-4 h-4 text-gray-500" />
  }
}

// colored badge for alert type
function AlertTypeBadge({ type }: { type: TrendAlert['alert_type'] }) {
  const colors = {
    bullish: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    bearish: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    volatile: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    momentum: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  }

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colors[type]}`}>
      {type}
    </span>
  )
}

export default function AIInsightsCard() {
  const [showAllAlerts, setShowAllAlerts] = useState(false)
  const [showAllObservations, setShowAllObservations] = useState(false)
  const [showSectorAnalysis, setShowSectorAnalysis] = useState(false)

  const { data, isLoading, isError, error } = useAIInsights()
  const refreshMutation = useRefreshAIInsights()

  const handleRefresh = () => {
    refreshMutation.mutate()
  }

  if (data?.status === 'not_configured') {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Insights</h2>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <AlertCircle className="w-12 h-12 text-gray-400 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-2">AI insights not configured</p>
          <p className="text-sm text-gray-500 dark:text-gray-500">
            Set ANTHROPIC_API_KEY to enable AI-powered market analysis
          </p>
        </div>
      </div>
    )
  }

  // Show spinner while loading
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Insights</h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        </div>
      </div>
    )
  }

  // Show error with retry button
  if (isError) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Insights</h2>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-2">Failed to load insights</p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mb-4">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <button
            onClick={handleRefresh}
            disabled={refreshMutation.isPending}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // Show empty state with generate button
  if (!data?.insights) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Insights</h2>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Sparkles className="w-12 h-12 text-gray-400 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-2">No insights available yet</p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mb-4">
            Insights are generated every 15 minutes from news data
          </p>
          <button
            onClick={handleRefresh}
            disabled={refreshMutation.isPending}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {refreshMutation.isPending ? 'Generating...' : 'Generate Now'}
          </button>
        </div>
      </div>
    )
  }

  // Extract data for rendering
  const { insights, is_generating } = data
  const alerts = insights.trend_alerts || []
  const observations = insights.key_observations || []

  // Only show first 2 items unless expanded
  const displayedAlerts = showAllAlerts ? alerts : alerts.slice(0, 2)
  const displayedObservations = showAllObservations ? observations : observations.slice(0, 2)

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      {/* Card header with title and refresh button */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Insights</h2>
            {/* Show when insights were generated */}
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Clock className="w-3.5 h-3.5" />
              <span>Updated {formatTimeAgo(insights.generated_at)}</span>
              {/* Show stale badge if insights are old */}
              {insights.is_stale && (
                <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded">
                  stale
                </span>
              )}
            </div>
          </div>
        </div>
        {/* Refresh button - spins when generating */}
        <button
          onClick={handleRefresh}
          disabled={refreshMutation.isPending || is_generating}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
          title="Refresh insights"
        >
          <RefreshCw
            className={`w-5 h-5 text-gray-500 dark:text-gray-400 ${
              refreshMutation.isPending || is_generating ? 'animate-spin' : ''
            }`}
          />
        </button>
      </div>

      {/* Show warning if rate limited */}
      {refreshMutation.data?.status === 'rate_limited' && (
        <div className="mb-4 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <p className="text-sm text-yellow-700 dark:text-yellow-400">
            Rate limited. Please wait {refreshMutation.data.retry_after}s before refreshing.
          </p>
        </div>
      )}

      {/* Market summary - main paragraph */}
      <div className="mb-6">
        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{insights.market_summary}</p>
      </div>

      {/* Trend alerts - ticker-specific signals */}
      {alerts.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Trend Alerts</h3>
          <div className="space-y-2">
            {displayedAlerts.map((alert, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800"
              >
                <AlertTypeIcon type={alert.alert_type} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-gray-900 dark:text-white">
                      ${alert.ticker}
                    </span>
                    <AlertTypeBadge type={alert.alert_type} />
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{alert.message}</p>
                </div>
              </div>
            ))}
          </div>
          {/* Show more/less button if more than 2 alerts */}
          {alerts.length > 2 && (
            <button
              onClick={() => setShowAllAlerts(!showAllAlerts)}
              className="mt-2 flex items-center gap-1 text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300"
            >
              {showAllAlerts ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Show {alerts.length - 2} more
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Key observations - bullet points */}
      {observations.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Key Observations
          </h3>
          <ul className="space-y-2">
            {displayedObservations.map((observation, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span className="text-purple-500 mt-1">•</span>
                <span>{observation}</span>
              </li>
            ))}
          </ul>
          {/* Show more/less button if more than 2 observations */}
          {observations.length > 2 && (
            <button
              onClick={() => setShowAllObservations(!showAllObservations)}
              className="mt-2 flex items-center gap-1 text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300"
            >
              {showAllObservations ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  Show {observations.length - 2} more
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Sector analysis - collapsible section */}
      {insights.sector_analysis && (
        <div className="mb-6">
          <button
            onClick={() => setShowSectorAnalysis(!showSectorAnalysis)}
            className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white mb-2"
          >
            {showSectorAnalysis ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
            Sector Analysis
          </button>
          {showSectorAnalysis && (
            <p className="text-sm text-gray-600 dark:text-gray-400 pl-6">
              {insights.sector_analysis}
            </p>
          )}
        </div>
      )}

      {/* Sentiment outlook - footer section */}
      {insights.sentiment_outlook && (
        <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Outlook</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">{insights.sentiment_outlook}</p>
        </div>
      )}
    </div>
  )
}
