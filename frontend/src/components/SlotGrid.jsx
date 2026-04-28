export default function SlotGrid({ slots, selectedSlot, onSelectSlot }) {
  const leftSlots = slots.slice(0, Math.ceil(slots.length / 2));
  const rightSlots = slots.slice(Math.ceil(slots.length / 2));
  const freeCount = slots.filter(s => s.status === 'free').length;
  const occupiedCount = slots.length - freeCount;
  const occupancyPct = slots.length > 0 ? Math.round((occupiedCount / slots.length) * 100) : 0;

  return (
    <div className="parking-lot-wrapper">
      <div className="parking-lot-container">

        {/* Header bar */}
        <div className="parking-lot-header">
          <span className="parking-lot-label">🅿 Parking Lot</span>
          <div className="parking-lot-stats">
            <span className="plh-stat free">🟢 {freeCount} Free</span>
            <span className="plh-stat occupied">🔴 {occupiedCount} Occupied</span>
          </div>
          <span className="parking-lot-entry">↑ ENTRY / EXIT</span>
        </div>

        {/* Occupancy bar */}
        <div className="lot-occupancy-bar-wrapper">
          <div className="lot-occupancy-bar">
            <div className="lot-occupancy-fill" style={{ width: `${occupancyPct}%` }} />
          </div>
          <span className="lot-occupancy-label">{occupancyPct}% occupied</span>
        </div>

        {/* Slot grid body */}
        <div className="parking-lot-body">
          <div className="parking-area">
            <div className="parking-col left-col">
              {leftSlots.map(slot => (
                <SlotCard key={slot.id} slot={slot} selectedSlot={selectedSlot} onSelectSlot={onSelectSlot} side="left" />
              ))}
            </div>

            <div className="driveway-vertical">
              <div className="driveway-arrow">▼</div>
              <div className="driveway-arrow">▼</div>
              <div className="driveway-arrow">▼</div>
            </div>

            <div className="parking-col right-col">
              {rightSlots.map(slot => (
                <SlotCard key={slot.id} slot={slot} selectedSlot={selectedSlot} onSelectSlot={onSelectSlot} side="right" />
              ))}
            </div>
          </div>

          {/* Legend */}
          <div className="parking-lot-legend">
            <span className="legend-item">
              <span className="legend-swatch free-swatch"></span>Free — Click to book
            </span>
            <span className="legend-item">
              <span className="legend-swatch selected-swatch"></span>Selected
            </span>
            <span className="legend-item">
              <span className="legend-swatch occupied-swatch"></span>Occupied
            </span>
          </div>
        </div>

      </div>
    </div>
  )
}

function SlotCard({ slot, selectedSlot, onSelectSlot, side }) {
  return (
    <div
      id={`slot-${slot.id}`}
      className={`map-slot ${slot.status === 'free' ? 'free' : 'occupied'} ${selectedSlot === slot.id ? 'selected' : ''}`}
      onClick={() => slot.status === 'free' && onSelectSlot(slot.id)}
      title={slot.status === 'free' ? 'Click to select' : `Occupied (Booking: ${slot.booking_id || ''})`}
    >
      <span className="slot-id">{slot.id}</span>
      <span className="slot-icon">{slot.status === 'free' ? '🚗' : '🔒'}</span>
    </div>
  );
}
