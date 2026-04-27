export default function SlotGrid({ slots, selectedSlot, onSelectSlot, mapImageUrl }) {
  const leftSlots = slots.slice(0, Math.ceil(slots.length / 2));
  const rightSlots = slots.slice(Math.ceil(slots.length / 2));

  return (
    <div className="parking-lot-wrapper">
      <div 
        className="satellite-map-container"
        style={{
          backgroundImage: mapImageUrl ? `url(${mapImageUrl})` : 'none',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        <div className="satellite-overlay">
          <div className="parking-area">
            <div className="parking-col left-col">
              {leftSlots.map(slot => (
                <SlotCard key={slot.id} slot={slot} selectedSlot={selectedSlot} onSelectSlot={onSelectSlot} side="left" />
              ))}
            </div>

            <div className="driveway-vertical"></div>

            <div className="parking-col right-col">
              {rightSlots.map(slot => (
                <SlotCard key={slot.id} slot={slot} selectedSlot={selectedSlot} onSelectSlot={onSelectSlot} side="right" />
              ))}
            </div>
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
