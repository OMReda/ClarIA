/**
 * datasetStore.ts — Persistent multi-dataset registry.
 *
 * Datasets are added here when a file upload succeeds and the backend
 * returns a validated file_id.  Switching between Dashboard and Aski
 * pages does not require re-uploading because the dataset lives here.
 *
 * The store is intentionally kept separate from AppState (store/index.ts)
 * so the two concerns don't bleed into each other.
 */
import { create } from 'zustand'
import type { ColumnInfo } from '../api/types'
import { getFileData } from '../api/client'

export interface Dataset {
  /** file_id returned by the backend — stable across page navigation */
  id: string
  name: string
  rowCount: number
  columns: ColumnInfo[]
  previewRows: Record<string, unknown>[]
  fullData?: Record<string, unknown>[]
  fullDataTruncated?: boolean
  uploadedAt: Date
}

interface DatasetState {
  datasets: Dataset[]
  /** The dataset currently selected for Dashboard or Aski work */
  activeId: string | null

  addDataset:    (d: Dataset) => void
  removeDataset: (id: string) => void
  setActive:     (id: string | null) => void
  getActive:     () => Dataset | undefined
  fetchFullData: (id: string) => Promise<void>
}

export const useDatasetStore = create<DatasetState>((set, get) => ({
  datasets: [],
  activeId: null,

  addDataset: (d) =>
    set((s) => ({
      datasets: [d, ...s.datasets.filter((x) => x.id !== d.id)],
      activeId: d.id,
    })),

  removeDataset: (id) =>
    set((s) => ({
      datasets: s.datasets.filter((x) => x.id !== id),
      activeId: s.activeId === id
        ? (s.datasets.find((x) => x.id !== id)?.id ?? null)
        : s.activeId,
    })),

  setActive: (id) => set({ activeId: id }),

  getActive: () => {
    const { datasets, activeId } = get()
    return datasets.find((d) => d.id === activeId)
  },

  fetchFullData: async (id: string) => {
    const s = get()
    const d = s.datasets.find((x) => x.id === id)
    // If we already have the full data, or dataset isn't found, do nothing
    if (!d || d.fullData) return

    try {
      const res = await getFileData(id)
      set((state) => ({
        datasets: state.datasets.map((x) => 
          x.id === id 
            ? { ...x, fullData: res.data, fullDataTruncated: res.is_truncated }
            : x
        )
      }))
    } catch (err) {
      console.error('Failed to fetch full data', err)
    }
  },
}))
