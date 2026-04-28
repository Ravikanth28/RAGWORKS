import { useState } from 'react'

export default function NLPInput({ onSend, onPrefill, onBook }) {
  const [text, setText] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [confirmed, setConfirmed] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!text.trim() || loading) return
    setLoading(true)
    setConfirmed(false)
    const result = await onSend(text)
    setResponse(result)
    setLoading(false)

    if (result?.action === 'book' && result?.prefill) {
      onPrefill(result.prefill)
    }
  }

  const examples = [
    { label: '📅 Book mall', text: 'Book parking near mall for 2 hours' },
    { label: '🔍 Check Anna Nagar', text: 'Show available slots at Anna Nagar' },
    { label: '🚗 Velachery 3h', text: 'Find parking in Velachery for 3 hours' },
    { label: '💰 Pricing', text: 'How much does parking cost at T Nagar' },
  ]

  const confidence = response?.parsed?.confidence
  const confColor = confidence >= 0.8 ? 'var(--accent-green)' : confidence >= 0.4 ? 'var(--accent-amber)' : 'var(--accent-red)'

  return (
    <div className="nlp-section">
      <div className="nlp-card">
        <div className="nlp-header">
          <span className="nlp-icon">🤖</span>
          <div>
            <h2>AI Smart Assistant</h2>
            <p className="nlp-subtitle">Powered by MCP Intent Engine + RAG Knowledge Base</p>
          </div>
          <div className="nlp-pipeline">
            <span className="pipeline-step">Guardrails</span>
            <span className="pipeline-arrow">→</span>
            <span className="pipeline-step">IntentEngine</span>
            <span className="pipeline-arrow">→</span>
            <span className="pipeline-step">RAG</span>
            <span className="pipeline-arrow">→</span>
            <span className="pipeline-step">Agent</span>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="nlp-input-row">
            <input
              id="nlp-input"
              className="input"
              type="text"
              placeholder='e.g. "Book parking near mall for 2 hours" or "Show slots at Anna Nagar"'
              value={text}
              onChange={e => setText(e.target.value)}
            />
            <button
              id="nlp-submit"
              className="btn btn-primary"
              type="submit"
              disabled={loading || !text.trim()}
            >
              {loading ? '⏳ Parsing...' : '🔍 Ask AI'}
            </button>
          </div>
        </form>

        <div className="nlp-examples">
          {examples.map(ex => (
            <button
              key={ex.text}
              className="btn btn-ghost example-chip"
              onClick={() => setText(ex.text)}
            >
              {ex.label}
            </button>
          ))}
        </div>

        {response && (
          <div className="nlp-response">
            {response.message && (
              <div className="nlp-response-message">
                <span className="nlp-response-icon">💬</span>
                <p className="message">{response.message}</p>
              </div>
            )}
            {response.parsed && (
              <div className="nlp-parsed">
                <span className="badge badge-cyan">
                  Intent: {response.parsed.intent}
                </span>
                {response.parsed.params?.location && (
                  <span className="badge badge-green">
                    📍 {response.parsed.params.location}
                  </span>
                )}
                {response.parsed.params?.duration && (
                  <span className="badge badge-amber">
                    ⏱ {response.parsed.params.duration}h
                  </span>
                )}
                {confidence !== undefined && (
                  <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: confColor }}>
                    Confidence: {(confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            )}
            {response.context && (
              <div className="nlp-rag-context">
                <span className="rag-label">📚 RAG Context</span>
                <p className="rag-text">{response.context}</p>
              </div>
            )}
            {response.action === 'book' && response.prefill?.location && response.parsed?.params?.duration && (
              <div className="nlp-confirm-row">
                {confirmed ? (
                  <span className="badge badge-green">✅ Booking confirmed!</span>
                ) : (
                  <button
                    className="btn btn-primary"
                    disabled={confirming}
                    onClick={async () => {
                      setConfirming(true)
                      const result = await onBook(response.prefill.location, response.parsed.params.duration)
                      setConfirming(false)
                      if (result) setConfirmed(true)
                    }}
                  >
                    {confirming ? '⏳ Booking...' : '✅ Confirm Booking'}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
