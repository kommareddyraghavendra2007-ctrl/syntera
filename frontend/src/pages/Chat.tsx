import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Send, Sparkles, RotateCcw, Network } from 'lucide-react'
import { queryApi } from '../api/query'
import CitationList from '../components/ui/CitationList'
import Spinner from '../components/ui/Spinner'
import { cn } from '../utils'
import type { Message } from '../types'

const DEMO_QUESTIONS = [
  'Where is authentication implemented?',
  'Explain the complete login flow',
  'What could be affected if I modify AuthService?',
  'What environment variables are required?',
  "I'm new here — what should I read first?",
]

export default function Chat() {
  const { repositoryId } = useParams<{ repositoryId: string }>()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<(Message & { graphData?: unknown })[]>([])
  const [conversationId, setConversationId] = useState<string | undefined>()
  const [includeGraph, setIncludeGraph] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const askMut = useMutation({
    mutationFn: (question: string) =>
      queryApi.ask(repositoryId!, question, conversationId, includeGraph),
    onSuccess: (data, question) => {
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 'u', role: 'user', content: question, citations: [] },
        {
          id: Date.now() + 'a',
          role: 'assistant',
          content: data.answer,
          citations: data.citations,
          graphData: data.graph_data,
        },
      ])
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id)
      }
    },
  })

  const handleSend = () => {
    const q = input.trim()
    if (!q || askMut.isPending) return
    setInput('')
    askMut.mutate(q)
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, askMut.isPending])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-syntera-400" />
          <h2 className="font-semibold text-white text-sm">Ask SYNTERA</h2>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={includeGraph}
              onChange={(e) => setIncludeGraph(e.target.checked)}
              className="accent-syntera-500"
            />
            <Network size={12} /> Include graph
          </label>
          {messages.length > 0 && (
            <button
              className="btn-ghost text-xs"
              onClick={() => { setMessages([]); setConversationId(undefined) }}
            >
              <RotateCcw size={12} />
              New chat
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Sparkles size={40} className="text-syntera-700 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">Ask anything about this codebase</h3>
            <p className="text-sm text-gray-500 mb-6">Every answer is grounded in real source evidence.</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-xl mx-auto">
              {DEMO_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); inputRef.current?.focus() }}
                  className="text-xs px-3 py-1.5 rounded-full bg-surface-tertiary border border-surface-border text-gray-400 hover:text-gray-200 hover:border-syntera-700 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {askMut.isPending && (
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-full bg-syntera-900 border border-syntera-700 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Sparkles size={12} className="text-syntera-400" />
            </div>
            <div className="card px-4 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-syntera-400 animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {askMut.isError && (
          <div className="card p-4 border-red-900/50 bg-red-900/10">
            <p className="text-red-400 text-sm">{askMut.error.message}</p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-surface-border">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            className="input resize-none flex-1"
            rows={2}
            placeholder="Ask a question about this repository…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <button
            className="btn-primary py-3 px-4"
            onClick={handleSend}
            disabled={!input.trim() || askMut.isPending}
          >
            {askMut.isPending ? <Spinner className="h-4 w-4" /> : <Send size={16} />}
          </button>
        </div>
        <p className="text-[10px] text-gray-600 mt-2">
          Enter to send · Shift+Enter for newline · Answers grounded in retrieved source evidence
        </p>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message & { graphData?: unknown } }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex items-start gap-3', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-xs font-bold',
          isUser
            ? 'bg-surface-tertiary border border-surface-border text-gray-400'
            : 'bg-syntera-900 border border-syntera-700 text-syntera-400',
        )}
      >
        {isUser ? 'U' : <Sparkles size={12} />}
      </div>

      <div className={cn('max-w-3xl space-y-3', isUser && 'items-end')}>
        <div className={cn('card px-4 py-3', isUser && 'bg-surface-tertiary')}>
          <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        </div>
        {!isUser && message.citations.length > 0 && (
          <div className="card px-4 py-3">
            <CitationList citations={message.citations} />
          </div>
        )}
      </div>
    </div>
  )
}
