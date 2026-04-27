import { useState, useEffect, useCallback } from 'react'

const API = '/api'

export function useParking() {
  const [locations, setLocations] = useState([])
  const [selectedLocation, setSelectedLocation] = useState(null)
  const [slots, setSlots] = useState([])
  const [slotMeta, setSlotMeta] = useState({})
  const [activeBookings, setActiveBookings] = useState([])
  const [loading, setLoading] = useState(false)
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  const fetchLocations = useCallback(async () => {
    try {
      const res = await fetch(`${API}/locations`)
      const data = await res.json()
      setLocations(data.locations || [])
    } catch (err) {
      addToast('Failed to load locations', 'error')
    }
  }, [addToast])

  const fetchSlots = useCallback(async (locationId) => {
    if (!locationId) return
    setLoading(true)
    try {
      const res = await fetch(`${API}/slots?location=${locationId}`)
      const data = await res.json()
      setSlots(data.slots || [])
      setSlotMeta({
        location: data.location,
        address: data.address,
        ratePerHour: data.ratePerHour,
        totalSlots: data.totalSlots,
        availableSlots: data.availableSlots,
        mapImageUrl: data.mapImageUrl,
      })
    } catch (err) {
      addToast('Failed to load slots', 'error')
    } finally {
      setLoading(false)
    }
  }, [addToast])

  const fetchBookings = useCallback(async () => {
    try {
      const res = await fetch(`${API}/bookings`)
      const data = await res.json()
      setActiveBookings(data.bookings || [])
    } catch (err) {
      // silent
    }
  }, [])

  const bookSlot = useCallback(async (locationId, duration, slotId = null) => {
    try {
      const body = { location: locationId, duration }
      if (slotId) body.slot_id = slotId
      const res = await fetch(`${API}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) {
        addToast(data.error || 'Booking failed', 'error')
        return null
      }
      addToast(data.message, 'success')
      await fetchLocations()
      await fetchSlots(locationId)
      await fetchBookings()
      return data.booking
    } catch (err) {
      addToast('Network error during booking', 'error')
      return null
    }
  }, [addToast, fetchLocations, fetchSlots, fetchBookings])

  const releaseSlot = useCallback(async (bookingId) => {
    try {
      const res = await fetch(`${API}/release`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: bookingId }),
      })
      const data = await res.json()
      if (!res.ok) {
        addToast(data.error || 'Release failed', 'error')
        return false
      }
      addToast(data.message, 'success')
      await fetchLocations()
      if (selectedLocation) await fetchSlots(selectedLocation)
      await fetchBookings()
      return true
    } catch (err) {
      addToast('Network error during release', 'error')
      return false
    }
  }, [addToast, fetchLocations, fetchSlots, fetchBookings, selectedLocation])

  const sendNLP = useCallback(async (text) => {
    try {
      const res = await fetch(`${API}/nlp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      return await res.json()
    } catch (err) {
      addToast('NLP request failed', 'error')
      return null
    }
  }, [addToast])

  const selectLocation = useCallback((locId) => {
    setSelectedLocation(locId)
    fetchSlots(locId)
  }, [fetchSlots])

  useEffect(() => {
    fetchLocations()
    fetchBookings()
    const interval = setInterval(fetchBookings, 15000)
    return () => clearInterval(interval)
  }, [fetchLocations, fetchBookings])

  return {
    locations, selectedLocation, selectLocation,
    slots, slotMeta, loading,
    activeBookings, bookSlot, releaseSlot,
    fetchLocations, fetchSlots, fetchBookings,
    sendNLP, toasts, addToast,
  }
}
