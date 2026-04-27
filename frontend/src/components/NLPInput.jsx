import { useState } from 'react'

export default function NLPInput({ onSend, onPrefill }) {
  const [text, setText] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!text.trim() || loading) return
    setLoading(true)
    const result = await onSend(text)
    setResponse(result)
    setLoading(false)

    // If the NLP returned a prefill action, pass it up
    if (result?.action === 'book' && result?.prefill) {
      onPrefill(result.prefill)
    }
  }

  const examples = [
    'Book parking near mall for 2 hours',
    'Show slots at Anna Nagar',
    'Find parking in Velachery for 3 hours',
  ]

  return (
    <div className="nlp-section">
      <div className="nlp-card">
        <div className="nlp-header">
          <span className="nlp-icon">🤖</span>
          <h2>Smart Assistant — Natural Language Input</h2>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="nlp-input-row">
            <input
              id="nlp-input"
              className="input"
              type="text"
              placeholder='Try: "Book parking near mall for 2 hours"'
              value={text}
              onChange={e => setText(e.target.value)}
            />
            <button
              id="nlp-submit"
              className="btn btn-primary"
              type="submit"
              disabled={loading || !text.trim()}
            >
              {loading ? '⏳' : '🔍'} Parse
            </button>
          </div>
        </form>

        <div style={{ marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {examples.map(ex => (
            <button
              key={ex}
              className="btn btn-ghost"
              style={{ fontSize: '0.75rem', padding: '6px 12px' }}
              onClick={() => setText(ex)}
            >
              {ex}
            </button>
          ))}
        </div>

        {response && (
          <div className="nlp-response">
            {response.message && <p className="message">{response.message}</p>}
            {response.parsed && (
              <div className="nlp-parsed">
                <span className="badge badge-cyan">Intent: {response.parsed.intent}</span>
                {response.parsed.params?.location && (
                  <span className="badge badge-green">Location: {response.parsed.params.location}</span>
                )}
                {response.parsed.params?.duration && (
                  <span className="badge badge-amber">Duration: {response.parsed.params.duration}h</span>
                )}
                <span className="badge badge-cyan">Confidence: {(response.parsed.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
