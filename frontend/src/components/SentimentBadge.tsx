import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { Sentiment } from '../types'

interface SentimentBadgeProps {
  sentiment: Sentiment | null
  size?: 'sm' | 'md' | 'lg'
  showScore?: boolean
}

export default function SentimentBadge({
  sentiment,
  size = 'md',
  showScore = false,
}: SentimentBadgeProps) {
  if (!sentiment) {
    return (
      <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded-full dark:bg-gray-800 dark:text-gray-400">
        <Minus className="w-3 h-3 mr-1" />
        N/A
      </span>
    )
  }

  const { label, score } = sentiment

  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }

  const iconSize = {
    sm: 'w-3 h-3',
    md: 'w-3 h-3',
    lg: 'w-4 h-4',
  }

  if (label === 'positive') {
    return (
      <span
        className={`inline-flex items-center font-medium text-green-700 bg-green-100 rounded-full dark:bg-green-900/30 dark:text-green-400 ${sizeClasses[size]}`}
      >
        <TrendingUp className={`${iconSize[size]} mr-1`} />
        {showScore ? `+${(score * 100).toFixed(0)}%` : 'Bullish'}
      </span>
    )
  }

  if (label === 'negative') {
    return (
      <span
        className={`inline-flex items-center font-medium text-red-700 bg-red-100 rounded-full dark:bg-red-900/30 dark:text-red-400 ${sizeClasses[size]}`}
      >
        <TrendingDown className={`${iconSize[size]} mr-1`} />
        {showScore ? `${(score * 100).toFixed(0)}%` : 'Bearish'}
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center font-medium text-gray-600 bg-gray-100 rounded-full dark:bg-gray-800 dark:text-gray-400 ${sizeClasses[size]}`}
    >
      <Minus className={`${iconSize[size]} mr-1`} />
      Neutral
    </span>
  )
}
