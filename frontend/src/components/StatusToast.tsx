import React, { useEffect, useRef, useState } from 'react'
import { useStore } from '../store'
import type { Toast, ToastSeverity } from '../store'
import { IconCheck, IconX, IconWarning, IconInfo, IconTrash, IconEdit } from './Icon'

const ICONS: Record<ToastSeverity, React.ReactNode> = {
  success: <IconCheck size={14} strokeWidth={2.5} />,
  error:   <IconX    size={14} strokeWidth={2.25} />,
  warning: <IconWarning size={14} strokeWidth={2} />,
  info:    <IconInfo size={14} strokeWidth={2} />,
  deleted: <IconTrash size={14} strokeWidth={2} />,
  modified: <IconEdit size={14} strokeWidth={2} />,
}

const TITLES: Record<ToastSeverity, string> = {
  success: 'Succès',
  error:   'Erreur',
  warning: 'Attention',
  info:    'Information',
  deleted: 'Suppression',
  modified: 'Modification',
}

function ToastItem({ item, onClose }: { item: Toast; onClose: (id: string) => void }) {
  const [exiting, setExiting] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleDismiss = () => {
    if (exiting) return
    setExiting(true)
    setTimeout(() => {
      onClose(item.id)
    }, 350) // Match CSS exit animation duration
  }

  useEffect(() => {
    timerRef.current = setTimeout(() => handleDismiss(), 4650)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [item.id])

  return (
    <div
      className={`toast toast--${item.severity} ${exiting ? 'toast--exiting' : 'toast--visible'}`}
      role="alert"
      aria-live="assertive"
      id={`toast-${item.id}`}
    >
      <div className="toast__icon" aria-hidden="true">
        {ICONS[item.severity]}
      </div>
      <div className="toast__body">
        <p className="toast__title">{TITLES[item.severity]}</p>
        <p className="toast__message">{item.message}</p>
      </div>
      <button
        className="toast__close"
        onClick={handleDismiss}
        aria-label="Fermer la notification"
      >
        <IconX size={12} strokeWidth={2.25} />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const { toasts, dismissToast } = useStore()

  return (
    <div
      className="toast-container"
      aria-label="Notifications"
      role="region"
      id="toast-container"
      style={{ pointerEvents: toasts.length ? 'auto' : 'none' }}
    >
      {toasts.map(t => (
        <ToastItem key={t.id} item={t} onClose={dismissToast} />
      ))}
    </div>
  )
}
