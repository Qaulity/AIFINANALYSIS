import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Articles from './pages/Articles'
import TickerAnalysis from './pages/TickerAnalysis'
import Trends from './pages/Trends'
import NLPAnalysis from './pages/NLPAnalysis'
import Markets from './pages/Markets'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="articles" element={<Articles />} />
          <Route path="markets" element={<Markets />} />
          <Route path="tickers/:symbol" element={<TickerAnalysis />} />
          <Route path="trends" element={<Trends />} />
          <Route path="nlp" element={<NLPAnalysis />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
