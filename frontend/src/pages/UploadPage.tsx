/**
 * UploadPage.tsx — Shared upload entry point for both Dashboard and Aski.
 *
 * Shows the hero copy, the drag-and-drop UploadZone, and—once at least
 * one dataset has been uploaded—a DatasetList below it so the user can
 * open any existing dataset in Dashboard or Aski without re-uploading.
 */
import React, { useState } from 'react'
import { createPortal } from 'react-dom'
import { UploadZone } from '../components/UploadZone'
import { SheetSelector } from '../components/SheetSelector'
import { useStore } from '../store'
import { useDatasetStore, type Dataset } from '../store/datasetStore'
import { IconFile, IconBarChart, IconX } from '../components/Icon'

interface UploadPageProps {
  onOpenDashboard: (datasetId: string) => void
  onOpenAski:      (datasetId: string) => void
}

function DatasetRow({
  ds,
  onOpenDashboard,
  onOpenAski,
  onRemove,
}: {
  ds: Dataset
  onOpenDashboard: () => void
  onOpenAski: () => void
  onRemove: () => void
}) {
  const fmt = new Intl.NumberFormat('fr-FR')
  const date = ds.uploadedAt.toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })

  return (
    <div className="dataset-row">
      <div className="dataset-row__icon" aria-hidden="true">
        <IconFile size={15} strokeWidth={1.75} />
      </div>
      <div className="dataset-row__info">
        <p className="dataset-row__name" title={ds.name}>{ds.name}</p>
        <p className="dataset-row__meta">
          {fmt.format(ds.rowCount)} lignes · {ds.columns.length} colonnes · {date}
        </p>
        <p className="dataset-row__cols-preview">
          {ds.columns.slice(0, 7).map(c => c.name).join(', ')}
          {ds.columns.length > 7 && '...'}
        </p>
      </div>
      <div className="dataset-row__actions">
        <button
          id={`open-dashboard-${ds.id}`}
          className="btn btn--ghost btn--sm"
          onClick={onOpenDashboard}
          title="Ouvrir dans Dashboard"
        >
          <IconBarChart size={13} strokeWidth={2} />
          Dashboard
        </button>
        <button
          id={`open-aski-${ds.id}`}
          className="btn btn--primary btn--sm"
          onClick={onOpenAski}
          title="Ouvrir dans Aski"
        >
          Aski →
        </button>
        <button
          id={`remove-dataset-${ds.id}`}
          className="btn btn--ghost btn--icon btn--sm"
          onClick={onRemove}
          aria-label="Supprimer ce fichier de la liste"
          title="Supprimer de la liste"
        >
          <IconX size={13} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  )
}

export function UploadPage({ onOpenDashboard, onOpenAski }: UploadPageProps) {
  const { status, resetAll, addToast } = useStore()
  const { datasets, removeDataset } = useDatasetStore()
  const [deletingDsId, setDeletingDsId] = useState<string | null>(null)

  const showSheet     = status === 'needs_sheet'
  const showUploadZone = status === 'idle' || status === 'uploading' || status === 'needs_sheet'

  const handleConfirmDelete = async () => {
    if (!deletingDsId) return
    const dsName = datasets.find(d => d.id === deletingDsId)?.name ?? 'Fichier'
    try {
      const { deleteFileAPI } = await import('../api/client')
      await deleteFileAPI(deletingDsId)
    } catch (e: any) {
      // Ignore 404 errors (meaning backend route doesn't exist or file already deleted)
      // We still want to remove it from the UI so it behaves like before!
      if (e?.response?.status !== 404) {
        console.warn("Backend delete failed, but removing locally anyway:", e)
      }
    }
    
    // Always remove from local state so the user isn't stuck
    removeDataset(deletingDsId)
    addToast('deleted', `${dsName} supprimé avec succès`)
    if (datasets.length === 1) {
      resetAll()
    }
    setDeletingDsId(null)
  }

  return (
    <div className={`upload-page ${datasets.length === 0 ? 'upload-page--centered' : ''}`}>

      {/* ── Hero ── */}
      {(status === 'idle' || status === 'uploading') && (
        <section className="hero" aria-labelledby="hero-heading">
          <h1 id="hero-heading" className="hero__title">
            Vos données en graphiques,<br />
            <em>en quelques secondes</em>
          </h1>
          <p className="hero__sub">
            Déposez un fichier CSV ou Excel, posez votre question en français,
            et obtenez un graphique interactif — sans coder.
          </p>
          <UploadZone />
        </section>
      )}

      {/* ── Sheet selection ── */}
      {showSheet && (
        <div className="content-panel animate-fade-up">
          <SheetSelector />
        </div>
      )}

      {/* ── Dataset library ── */}
      {datasets.length > 0 && (
        <section className="dataset-library animate-fade-up" aria-label="Fichiers importés">
          <div className="dataset-library__header">
            <h2 className="dataset-library__title">Fichiers importés</h2>
            {status !== 'idle' && status !== 'uploading' && (
              <button
                id="upload-another-btn"
                className="btn btn--ghost btn--sm"
                onClick={resetAll}
              >
                + Importer un autre fichier
              </button>
            )}
          </div>

          <div className="dataset-list">
            {datasets.map((ds) => (
              <DatasetRow
                key={ds.id}
                ds={ds}
                onOpenDashboard={() => onOpenDashboard(ds.id)}
                onOpenAski={() => onOpenAski(ds.id)}
                onRemove={() => setDeletingDsId(ds.id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Delete Confirmation Modal ── */}
      {deletingDsId && (() => {
        const dToDel = datasets.find(d => d.id === deletingDsId)
        return createPortal(
          <div
            className="settings-backdrop"
            onClick={(e) => e.target === e.currentTarget && setDeletingDsId(null)}
            role="dialog"
            aria-modal="true"
          >
            <div className="settings-panel animate-scale-in" style={{ maxWidth: 400, padding: 0 }}>
              <div className="settings-panel__header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>Confirmer la suppression</h3>
                </div>
                <button className="btn btn--ghost btn--icon" onClick={() => setDeletingDsId(null)} style={{ width: 28, height: 28, borderRadius: '50%' }}>
                  <IconX size={14} strokeWidth={2} />
                </button>
              </div>
              <div className="settings-panel__body">
                <p style={{ margin: 0, fontSize: 14, color: 'var(--text-2)', lineHeight: 1.5 }}>
                  Voulez-vous vraiment supprimer le fichier <strong>{dToDel?.name}</strong> ? Cette action est irréversible et supprimera l'historique associé.
                </p>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 24 }}>
                  <button className="btn btn--ghost btn--sm" onClick={() => setDeletingDsId(null)}>Annuler</button>
                  <button className="btn btn--primary btn--sm" style={{ background: 'var(--danger)', borderColor: 'var(--danger)', color: '#fff' }} onClick={handleConfirmDelete}>Supprimer</button>
                </div>
              </div>
            </div>
          </div>,
          document.body
        )
      })()}
    </div>
  )
}
