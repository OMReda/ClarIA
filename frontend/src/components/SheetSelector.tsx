import React, { useState } from 'react'
import { FileSpreadsheet } from 'lucide-react'
import { selectSheet } from '../api/client'
import { useStore } from '../store'

export function SheetSelector() {
  const { sheetNames, fileId, setUploadResult, addToast, setStatus } = useStore()
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (!sheetNames?.length) return null

  async function confirm() {
    if (!selected || !fileId) return
    setLoading(true)
    try {
      const res = await selectSheet(fileId, selected)
      const currentName = useStore.getState().fileName ?? ''
      const newName = currentName.includes(`— ${selected}`) ? currentName : `${currentName} — ${selected}`
      setUploadResult({ ...res, status: 'validated' }, newName)
      addToast('success', `Feuille "${selected}" chargée.`)
    } catch (err: any) {
      addToast('error', err?.response?.data?.error?.message ?? 'Erreur lors de la sélection.')
      setStatus('idle')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sheet-selector card" id="sheet-selector" role="region" aria-label="Sélection de la feuille Excel">
      <div className="sheet-selector__icon" aria-hidden="true">
        <FileSpreadsheet size={26} strokeWidth={1.5} style={{ color: 'var(--blue)' }} />
      </div>

      <h2 className="sheet-selector__title">Choisissez une feuille</h2>
      <p className="sheet-selector__sub">
        Ce fichier contient {sheetNames.length} feuilles. Sélectionnez celle que vous souhaitez analyser.
      </p>

      <div className="sheet-list" role="list">
        {sheetNames.map((name) => (
          <button
            key={name}
            id={`sheet-btn-${name}`}
            role="listitem"
            className={`sheet-btn${selected === name ? ' sheet-btn--active' : ''}`}
            onClick={() => setSelected(name)}
            type="button"
            aria-pressed={selected === name}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <line x1="3" y1="9" x2="21" y2="9"/>
              <line x1="9" y1="21" x2="9" y2="9"/>
            </svg>
            {name}
            {selected === name && (
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M20 6L9 17l-5-5"/>
              </svg>
            )}
          </button>
        ))}
      </div>

      <button
        id="confirm-sheet-btn"
        className="btn btn--primary"
        onClick={confirm}
        disabled={!selected || loading}
      >
        {loading
          ? <><span className="spinner spinner--sm spinner--inv" /> Chargement…</>
          : <>Analyser cette feuille</>
        }
      </button>
    </div>
  )
}
