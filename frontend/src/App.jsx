import { useState, useCallback } from 'react'
import './App.css'
import { useParking } from './hooks/useParking'
import LocationSelector from './components/LocationSelector'
import SlotGrid from './components/SlotGrid'
import BookingPanel from './components/BookingPanel'
import ActiveBookings from './components/ActiveBookings'
import NLPInput from './components/NLPInput'

function App() {
  const {
    locations, selectedLocation, selectLocation,
    slots, slotMeta, loading,
    activeBookings, bookSlot, releaseSlot,
    fetchLocations, fetchSlots, fetchBookings,
    sendNLP, toasts,
  } = useParking()

  const [selectedSlot, setSelectedSlot] = useState(null)

  const totalAvailable = locations.reduce((s, l) => s + l.availableSlots, 0)
  const totalSlots = locations.reduce((s, l) => s + l.totalSlots, 0)

  const handleBook = useCallback(async (duration, slotId) => {
    if (!selectedLocation) return
    const result = await bookSlot(selectedLocation, duration, slotId)
    if (result) setSelectedSlot(null)
  }, [selectedLocation, bookSlot])

  const handleNLPPrefill = useCallback((prefill) => {
    if (prefill.location) {
      selectLocation(prefill.location)
    }
  }, [selectLocation])

  const handleRefresh = useCallback(() => {
    fetchLocations()
    fetchBookings()
    if (selectedLocation) fetchSlots(selectedLocation)
  }, [fetchLocations, fetchBookings, fetchSlots, selectedLocation])

  return (
    <div className="app">
      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span>{t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : 'ℹ️'}</span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="header">
        <div className="header-inner">
          <div className="header-brand">
            <div className="header-logo">🅿️</div>
            <div>
              <div className="header-title">Smart Parking Slot Booker</div>
              <div className="header-subtitle">MCP — Model Context Protocol</div>
            </div>
          </div>
          <div className="header-stats">
            <div className="header-stat">
              <div className="header-stat-value">{locations.length}</div>
              <div className="header-stat-label">Locations</div>
            </div>
            <div className="header-stat">
              <div className="header-stat-value">{totalAvailable}</div>
              <div className="header-stat-label">Available</div>
            </div>
            <div className="header-stat">
              <div className="header-stat-value">{totalSlots}</div>
              <div className="header-stat-label">Total Slots</div>
            </div>
            <div className="header-stat">
              <div className="header-stat-value">{activeBookings.length}</div>
              <div className="header-stat-label">Active</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main">
        {/* NLP Smart Input */}
        <NLPInput onSend={sendNLP} onPrefill={handleNLPPrefill} />

        {/* Content Grid */}
        <div className="content-grid">
          {/* Locations Sidebar */}
          <LocationSelector
            locations={locations}
            selectedLocation={selectedLocation}
            onSelect={(id) => { selectLocation(id); setSelectedSlot(null); }}
          />

          {/* Slots Main Area */}
          <div className="slots-panel">
            {selectedLocation ? (
              <>
                <div className="slots-panel-header">
                  <div>
                    <h2>{slotMeta.location || 'Loading...'}</h2>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                      {slotMeta.address}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <span className="badge badge-green">
                      {slotMeta.availableSlots} Free
                    </span>
                    <span className="badge badge-red">
                      {(slotMeta.totalSlots || 0) - (slotMeta.availableSlots || 0)} Occupied
                    </span>
                  </div>
                </div>

                {loading ? (
                  <div className="empty-state">
                    <div className="empty-state-icon" style={{ animation: 'pulse 1s infinite' }}>⏳</div>
                    <h3>Loading slots...</h3>
                  </div>
                ) : (
                  <>
                    <SlotGrid
                      slots={slots}
                      selectedSlot={selectedSlot}
                      onSelectSlot={setSelectedSlot}
                      mapImageUrl={slotMeta.mapImageUrl}
                    />
                    <BookingPanel
                      selectedSlot={selectedSlot}
                      slotMeta={slotMeta}
                      onBook={handleBook}
                    />
                  </>
                )}
              </>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🏢</div>
                <h3>Select a Location</h3>
                <p>Choose a parking location from the left panel to view available slots.</p>
              </div>
            )}
          </div>
        </div>

        {/* Active Bookings */}
        <ActiveBookings
          bookings={activeBookings}
          onRelease={releaseSlot}
          onRefresh={handleRefresh}
        />
      </main>
    </div>
  )
}

export default App
