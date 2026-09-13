import React, { useCallback, useRef, useState } from 'react'
import { uploadFile } from '../api/client'
import { useStore } from '../store'
import { useDatasetStore } from '../store/datasetStore'

export function UploadZone() {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const { setUploadResult, addToast, setStatus, config } = useStore()

  const handleFile = useCallback(async (file: File) => {
    // Client-side validation
    const maxSize = (config?.max_file_size_mb || 10) * 1024 * 1024
    const allowedExtensions = ['.csv', '.xlsx', '.xls']
    const isExtensionValid = allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext))

    if (!isExtensionValid) {
      addToast('error', 'Format de fichier non supporté. Veuillez utiliser un fichier CSV ou Excel (.xlsx, .xls).')
      return
    }

    if (file.size > maxSize) {
      addToast('error', `Fichier trop volumineux. La limite est de ${config?.max_file_size_mb || 10} Mo.`)
      return
    }

    setUploading(true)
    setStatus('uploading')
    useDatasetStore.getState().setActive(null)
    try {
      const res = await uploadFile(file)
      setUploadResult(res, file.name)
      addToast('success', `"${file.name}" importé avec succès.`)
    } catch (err: any) {
      console.error('Import error:', err)
      let msg = 'Une erreur est survenue lors de l\'import.'
      if (err?.name === 'ZodError') {
        msg = 'Erreur de validation des données du serveur.'
      } else if (typeof err?.response?.data?.detail === 'string') {
        msg = err.response.data.detail
      } else if (err?.response?.data?.detail?.error?.message) {
        msg = err.response.data.detail.error.message
      } else if (err?.response?.data?.error?.message) {
        msg = err.response.data.error.message
      } else if (err?.message) {
        msg = `${msg} (${err.message})`
      }
      addToast('error', msg)
      setStatus('idle')
    } finally {
      setUploading(false)
    }
  }, [setUploadResult, addToast, setStatus, config])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  return (
    <div
      id="upload-zone"
      className={`upload-zone${dragging ? ' upload-zone--dragging' : ''}${uploading ? ' upload-zone--uploading' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      role="button"
      aria-label="Zone d'import de fichier — cliquer ou glisser-déposer"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        hidden
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        id="file-input"
      />

      <div className="upload-zone__icon" aria-hidden="true">
        {uploading ? (
          <div className="spinner" />
        ) : (
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        )}
      </div>

      <p className="upload-zone__title">
        {uploading ? 'Import en cours…' : 'Glissez votre fichier ici'}
      </p>
      <p className="upload-zone__sub">
        ou cliquez pour parcourir vos fichiers
      </p>

      {!uploading && (
        <button className="btn btn--primary" id="upload-btn" type="button" tabIndex={-1}>
          Choisir un fichier
        </button>
      )}

      <p className="upload-zone__hint">
        {config
          ? `CSV, Excel (.xlsx, .xls) · Maximum ${config.max_file_size_mb} Mo · ${config.max_rows.toLocaleString('fr-FR')} lignes`
          : `CSV, Excel (.xlsx, .xls) · Maximum 10 Mo · 100 000 lignes`
        }
      </p>
    </div>
  )
}
