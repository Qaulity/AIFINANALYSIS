import { useState, useEffect } from 'react'
import { Search, Filter, ChevronLeft, ChevronRight, Newspaper } from 'lucide-react'
import { useArticles } from '../hooks/useApi'
import ArticleCard from '../components/ArticleCard'

export default function Articles() {
  const [page, setPage] = useState(1)
  const [sentiment, setSentiment] = useState<string>('')
  const [source, setSource] = useState('')
  const [keyword, setKeyword] = useState('')
  const [debouncedKeyword, setDebouncedKeyword] = useState('')
  const [days, setDays] = useState(7)

  // Debounce keyword search to avoid too many API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedKeyword(keyword)
      setPage(1) // Reset to first page when keyword changes
    }, 300)
    return () => clearTimeout(timer)
  }, [keyword])

  const { data, isLoading, isFetching } = useArticles({
    page,
    per_page: 12,
    sentiment: sentiment || undefined,
    source: source || undefined,
    keyword: debouncedKeyword || undefined,
    days,
  })

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Articles</h1>
        <p className="mt-1 text-gray-500 dark:text-gray-400">
          Browse and filter financial news articles
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
        <div className="flex flex-col gap-4">
          {/* Keyword Search - Full Width */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search articles by keywords (e.g., layoff, earnings, china)..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {isFetching && keyword && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              </div>
            )}
          </div>

          {/* Secondary Filters Row */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Source Filter */}
            <div className="relative flex-1 min-w-[160px] max-w-[240px]">
              <Newspaper className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Filter by source..."
                value={source}
                onChange={(e) => {
                  setSource(e.target.value)
                  setPage(1)
                }}
                className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Sentiment Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={sentiment}
                onChange={(e) => {
                  setSentiment(e.target.value)
                  setPage(1)
                }}
                className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Sentiments</option>
                <option value="positive">Bullish</option>
                <option value="negative">Bearish</option>
                <option value="neutral">Neutral</option>
              </select>
            </div>

            {/* Time Range */}
            <select
              value={days}
              onChange={(e) => {
                setDays(Number(e.target.value))
                setPage(1)
              }}
              className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </select>

            {/* Active Filters Summary */}
            {(keyword || source || sentiment) && (
              <button
                onClick={() => {
                  setKeyword('')
                  setSource('')
                  setSentiment('')
                  setPage(1)
                }}
                className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {/* Article Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data?.articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>

          {/* Empty State */}
          {data?.articles.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 dark:text-gray-500 mb-4">
                <Search className="w-12 h-12 mx-auto" />
              </div>
              <p className="text-gray-500 dark:text-gray-400 mb-2">
                No articles found matching your criteria.
              </p>
              {(keyword || source || sentiment) && (
                <p className="text-sm text-gray-400 dark:text-gray-500">
                  Try adjusting your filters or search terms.
                </p>
              )}
            </div>
          )}

          {/* Pagination */}
          {data && data.total > data.per_page && (
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-800">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Showing {(page - 1) * data.per_page + 1} to{' '}
                {Math.min(page * data.per_page, data.total)} of {data.total} articles
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1 || isFetching}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-4 py-2 text-sm font-medium">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages || isFetching}
                  className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
