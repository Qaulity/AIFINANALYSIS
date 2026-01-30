import { format } from 'date-fns'
import { ExternalLink, User } from 'lucide-react'
import type { Article } from '../types'
import SentimentBadge from './SentimentBadge'

interface ArticleCardProps {
  article: Article
}

export default function ArticleCard({ article }: ArticleCardProps) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden hover:shadow-lg transition-shadow">
      {/* Image */}
      {article.image_url && (
        <div className="aspect-video bg-gray-100 dark:bg-gray-800">
          <img
            src={article.image_url}
            alt={article.title}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
        </div>
      )}

      {/* Content */}
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white line-clamp-2 flex-1">
            {article.title}
          </h3>
          <SentimentBadge sentiment={article.sentiment} showScore />
        </div>

        {/* Description */}
        {article.description && (
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-3">
            {article.description}
          </p>
        )}

        {/* Tickers */}
        {article.tickers.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {article.tickers.slice(0, 5).map((ticker) => (
              <span
                key={ticker}
                className="px-2 py-0.5 text-xs font-medium text-blue-700 bg-blue-100 rounded dark:bg-blue-900/30 dark:text-blue-400"
              >
                ${ticker}
              </span>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
          <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
            <span className="font-medium">{article.source_name}</span>
            {article.author && (
              <>
                <span className="mx-2">·</span>
                <User className="w-3.5 h-3.5 mr-1" />
                <span className="truncate max-w-[120px]">{article.author}</span>
              </>
            )}
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">
              {format(new Date(article.published_at), 'MMM d, yyyy h:mm a')}
            </span>
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
