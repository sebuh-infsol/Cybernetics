import { useState } from 'react'
import { Composer } from './components/Composer'
import { Header } from './components/Header'
import { MCPPage } from './components/MCPPage'

export default function App() {
  const [page, setPage] = useState<'composer' | 'mcp'>('composer')

  return (
    <div className="min-h-screen bg-slate-950">
      <Header page={page} onNavigate={setPage} />
      <main className="max-w-7xl mx-auto px-4 py-8">
        {page === 'composer' && <Composer />}
        {page === 'mcp' && <MCPPage />}
      </main>
    </div>
  )
}
