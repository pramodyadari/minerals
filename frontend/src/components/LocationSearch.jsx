import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Loader2, MapPin } from 'lucide-react';

export default function LocationSearch({ onLocationSelect, selectedLocation }) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Sync input when selectedLocation changes externally (e.g. map click or GPS)
  useEffect(() => {
    if (selectedLocation && selectedLocation.name) {
      setQuery(selectedLocation.name);
    }
  }, [selectedLocation]);

  // Handle outside click to close suggestions
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search query
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setSuggestions([]);
      return;
    }

    // Check if query is manual coordinate pair e.g. "21.85, 80.25"
    const coordMatch = query.match(/^([-+]?[0-9]*\.?[0-9]+)[\s,]+([-+]?[0-9]*\.?[0-9]+)$/);
    if (coordMatch) {
      const lat = parseFloat(coordMatch[1]);
      const lon = parseFloat(coordMatch[2]);
      if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        setSuggestions([
          {
            display_name: `Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`,
            lat: lat.toString(),
            lon: lon.toString(),
            is_coordinate: true
          }
        ]);
        setIsOpen(true);
        return;
      }
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const resp = await fetch(
          `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1`
        );
        if (resp.ok) {
          const data = await resp.json();
          setSuggestions(data);
          setIsOpen(true);
        }
      } catch (err) {
        console.warn('Geocoding error:', err);
      } finally {
        setIsLoading(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (item) => {
    const lat = parseFloat(item.lat);
    const lon = parseFloat(item.lon);
    const name = item.display_name.split(',')[0] || item.display_name;

    setQuery(name);
    setIsOpen(false);
    onLocationSelect({
      name: item.display_name,
      shortName: name,
      lat,
      lon
    });
  };

  const handleClear = () => {
    setQuery('');
    setSuggestions([]);
    setIsOpen(false);
  };

  return (
    <div className="search-overlay-bar" ref={dropdownRef}>
      <div className="search-input-group">
        <div className="search-icon-left">
          <Search size={18} />
        </div>
        <input
          type="text"
          className="search-input"
          placeholder="Search place, village, district, or coordinates (e.g. 21.85, 80.25)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
        />
        <div className="search-tools-right">
          {isLoading && <Loader2 size={16} className="animate-spin" color="#c6a052" />}
          {query && (
            <button className="clear-btn" onClick={handleClear} title="Clear search">
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {isOpen && suggestions.length > 0 && (
        <ul className="search-suggestions-list">
          {suggestions.map((item, idx) => (
            <li
              key={idx}
              className="suggestion-item"
              onClick={() => handleSelect(item)}
            >
              <div className="suggestion-title">
                <MapPin size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2, color: '#c6a052' }} />
                {item.display_name}
              </div>
              <div className="suggestion-coords">
                Lat: {parseFloat(item.lat).toFixed(4)} | Lon: {parseFloat(item.lon).toFixed(4)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
