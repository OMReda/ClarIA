import React, { useEffect, useRef } from 'react'
import { useStore } from '../store'
import type { Toast, ToastSeverity } from '../store'
import { IconCheck, IconX, IconWarning, IconInfo } from './Icon'

const ICONS: Record<ToastSeverity, React.ReactNode> = {
  success: <IconCheck size={14} strokeWidth={2.5} />,
  error:   <IconX    size={14} strokeWidth={2.25} />,
  warning: <IconWarning size={14} strokeWidth={2} />,
  info:    <IconInfo size={14} strokeWidth={2} />,
}

const TITLES: Record<ToastSeverity, string> = {
  success: 'Succès',
  error:   'Erreur',
  warning: 'Attention',
  info:    'Information',
}

function ToastItem({ item, onClose }: { item: Toast; onClose: (id: string) => void }) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    timerRef.current = setTimeout(() => onClose(item.id), 5000)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [item.id, onClose])

  return (
    <div
      className={`toast toast--${item.severity} toast--visible`}
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
        onClick={() => onClose(item.id)}
        aria-label="Fermer la notification"
      >
        <IconX size={12} strokeWidth={2.25} />
      </button>
    </div>
  )
}

import { useAutoAnimate } from '@formkit/auto-animate/react'

export function ToastContainer() {
  const { toasts, dismissToast } = useStore()
  const [parent] = useAutoAnimate<HTMLDivElement>({ duration: 250, easing: 'ease-out' })

  return (
    <div
      className="toast-container"
      aria-label="Notifications"
      role="region"
      id="toast-container"
      ref={parent}
      style={{ pointerEvents: toasts.length ? 'auto' : 'none' }}
    >
      {toasts.map(t => (
        <ToastItem key={t.id} item={t} onClose={dismissToast} />
      ))}
    </div>
  )
}
