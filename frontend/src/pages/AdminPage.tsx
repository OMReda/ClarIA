import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import autoAnimate from '@formkit/auto-animate'
import {
  fetchAdminUsers,
  createAdminUser,
  updateAdminUser,
  deleteAdminUser,
  setAdminUserPassword
} from '../api/client'
import { IconSettings, IconX, IconUser } from '../components/Icon'
import { useStore } from '../store'

function formatErr(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (!detail) return err?.message || fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => {
      let msg = d.msg || '';
      if (msg.startsWith('Value error, ')) {
        msg = msg.substring(13);
      }
      return msg;
    }).join(', ');
  }
  if (typeof detail === 'object') {
    return (detail as any).msg || (detail as any).message || JSON.stringify(detail);
  }
  return String(detail);
}

const getPwdRules = (pwd: string) => ({
  length: pwd.length >= 8,
  upper: /[A-Z]/.test(pwd),
  lower: /[a-z]/.test(pwd),
  digit: /\d/.test(pwd),
  special: /[!@#$%^&*(),.?":{}|<>]/.test(pwd)
});

const renderPasswordRules = (pwd: string) => {
  const rules = getPwdRules(pwd || '');
  const show = pwd && pwd.length > 0;
  
  const ruleStyle = (met: boolean) => ({
    color: met ? 'var(--success)' : 'var(--text-3)',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transform: met ? 'translateX(4px)' : 'translateX(0)',
    opacity: met ? 1 : 0.7
  });

  return (
    <div style={{ 
      marginTop: show ? '12px' : '0px', 
      fontSize: '12px', 
      display: 'flex', 
      flexDirection: 'column', 
      gap: '6px',
      overflow: 'hidden',
      transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
      maxHeight: show ? '150px' : '0px',
      opacity: show ? 1 : 0
    }}>
      <div style={ruleStyle(rules.length)}>
        <span>{rules.length ? '✓' : '○'}</span> Au moins 8 caractères
      </div>
      <div style={ruleStyle(rules.upper)}>
        <span>{rules.upper ? '✓' : '○'}</span> Au moins une lettre majuscule
      </div>
      <div style={ruleStyle(rules.lower)}>
        <span>{rules.lower ? '✓' : '○'}</span> Au moins une lettre minuscule
      </div>
      <div style={ruleStyle(rules.digit)}>
        <span>{rules.digit ? '✓' : '○'}</span> Au moins un chiffre
      </div>
      <div style={ruleStyle(rules.special)}>
        <span>{rules.special ? '✓' : '○'}</span> Au moins un caractère spécial
      </div>
    </div>
  );
};

/** Returns true if the Keycloak user record represents an admin account. */
function isAdminUser(u: any): boolean {
  return (
    u.username === 'adminuser' ||
    u.username === 'admin' ||
    (Array.isArray(u.realmRoles) && u.realmRoles.includes('admin'))
  )
}

export function AdminPage() {
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState<string | null>(null)
  const [userToDelete, setUserToDelete] = useState<any | null>(null)
  const [updatingStatusId, setUpdatingStatusId] = useState<string | null>(null)

  const addToast = useStore(s => s.addToast)

  // Form states
  const [formData, setFormData] = useState({
    username: '', email: '', firstName: '', lastName: '', password: '', enabled: true
  })
  const [isEmailModified, setIsEmailModified] = useState(false)

  const listRef = useRef<HTMLTableSectionElement>(null)

  useEffect(() => {
    if (listRef.current) {
      autoAnimate(listRef.current, { duration: 300, easing: 'ease-in-out' })
    }
  }, [listRef])

  useEffect(() => {
    loadUsers()
  }, [])

  async function loadUsers() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdminUsers()
      setUsers(data)
    } catch (err: any) {
      setError(formatErr(err, 'Failed to load users'))
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createAdminUser(formData)
      addToast('success', 'Utilisateur créé avec succès.')
      setShowCreate(false)
      fetchAdminUsers().then(setUsers).catch(() => { })
    } catch (err: any) {
      addToast('error', formatErr(err, 'Erreur lors de la création'))
    }
  }

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault()
    if (!showEdit) return
    try {
      await updateAdminUser(showEdit, {
        username: formData.username,
        email: formData.email,
        firstName: formData.firstName,
        lastName: formData.lastName,
        enabled: formData.enabled
      })
      if (formData.password && formData.password.trim() !== '') {
        await setAdminUserPassword(showEdit, { password: formData.password })
        addToast('modified', 'Profil, statut et mot de passe mis à jour avec succès.')
      } else {
        addToast('modified', 'Utilisateur mis à jour.')
      }
      setShowEdit(null)
      fetchAdminUsers().then(setUsers).catch(() => { })
    } catch (err: any) {
      addToast('error', formatErr(err, 'Erreur de mise à jour'))
    }
  }

  async function toggleUserStatus(u: any, targetStatus: boolean) {
    if (isAdminUser(u)) {
      addToast('error', "Le statut de l'administrateur ne peut pas être modifié.")
      return
    }
    if (targetStatus === u.enabled || updatingStatusId === u.id) return
    setUpdatingStatusId(u.id)
    // Optimistic UI update for instant feedback
    setUsers(prev => prev.map(x => x.id === u.id ? { ...x, enabled: targetStatus } : x))
    try {
      await updateAdminUser(u.id, {
        enabled: targetStatus
      })
      if (targetStatus) {
        addToast('modified', 'Utilisateur activé avec succès.')
      } else {
        addToast('modified', 'Utilisateur désactivé.')
      }
    } catch (err: any) {
      // Revert optimistic update on error
      setUsers(prev => prev.map(x => x.id === u.id ? { ...x, enabled: u.enabled } : x))
      addToast('error', formatErr(err, "Erreur lors de la modification du statut"))
    } finally {
      setUpdatingStatusId(null)
    }
  }

  function initiateDelete(u: any) {
    if (isAdminUser(u)) {
      addToast('error', "L'utilisateur administrateur ne peut pas être supprimé.")
      return
    }
    const nonAdminCount = users.filter(x => !isAdminUser(x)).length
    if (nonAdminCount <= 1) {
      addToast('error', "Impossible de supprimer : la plateforme doit posséder au moins un utilisateur (non-administrateur).")
      return
    }
    if (users.length <= 1) {
      addToast('error', "Impossible de supprimer : la plateforme doit posséder au moins un utilisateur.")
      return
    }
    setUserToDelete(u)
  }

  async function confirmDelete() {
    if (!userToDelete) return
    try {
      await deleteAdminUser(userToDelete.id)
      addToast('deleted', 'Utilisateur supprimé.')
      setUserToDelete(null)
      setUsers(prev => prev.filter(x => x.id !== userToDelete.id))
      fetchAdminUsers().then(setUsers).catch(() => { })
    } catch (err: any) {
      addToast('error', formatErr(err, 'Erreur de suppression'))
      setUserToDelete(null)
    }
  }

  function openEdit(u: any) {
    setFormData({
      username: u.username,
      email: u.email || '',
      firstName: u.firstName || '',
      lastName: u.lastName || '',
      password: '',
      enabled: u.enabled !== undefined ? u.enabled : true
    })
    setShowEdit(u.id)
  }

  function openCreate() {
    setFormData({ username: '', email: '', firstName: '', lastName: '', password: '', enabled: true })
    setIsEmailModified(false)
    setShowCreate(true)
  }

  const r = getPwdRules(formData.password || '');
  const isPwdValid = Boolean(formData.password && r.length && r.upper && r.lower && r.digit && r.special);

  const renderModal = (title: string, onClose: () => void, onSubmit: (e: React.FormEvent) => void, children: React.ReactNode, submitDisabled?: boolean) => createPortal(
    <div className="admin-modal-backdrop">
      <div className="admin-modal-panel">
        <div className="admin-modal__header">
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-1)' }}>{title}</h3>
          <button type="button" className="btn btn--ghost btn--icon" onClick={onClose}><IconX size={16} /></button>
        </div>
        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', width: '100%', boxSizing: 'border-box' }}>
          <div className="admin-modal__body">
            {children}
          </div>
          <div className="admin-modal__footer">
            <button type="button" className="btn btn--ghost" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn--primary" disabled={submitDisabled}>Enregistrer</button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  )

  return (
    <div className="admin-page">
      <div className="admin-header">
        <div>
          <h1 className="admin-header__title">Tableau de bord Administrateur</h1>
          <p className="admin-header__sub">Gérez les accès et les utilisateurs de la plateforme</p>
        </div>
        <button className="btn btn--primary btn--lg shadow-glow btn-pill" onClick={openCreate}>
          + Nouvel Utilisateur
        </button>
      </div>

      <div className="admin-card">
        {loading ? (
          <div className="admin-card__empty">
            <div className="spinner spinner--lg" style={{ marginBottom: '16px' }}></div>
            <p>Chargement des utilisateurs...</p>
          </div>
        ) : error ? (
          <div className="admin-card__empty" style={{ color: 'var(--danger)' }}>
            <p>{error}</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Nom d'utilisateur</th>
                  <th>Email</th>
                  <th>Nom complet</th>
                  <th style={{ textAlign: 'center' }}>Statut</th>
                  <th style={{ textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody ref={listRef}>
                {users.map(u => {
                  const isAdmin = isAdminUser(u)
                  const nonAdminCount = users.filter(x => !isAdminUser(x)).length
                  const isLastUser = !isAdmin && (nonAdminCount <= 1 || users.length <= 1)
                  const isDeleteDisabled = isAdmin || isLastUser
                  return (
                    <tr key={u.id}>
                      <td>
                        <div className="user-cell">
                          <div className="user-avatar">{u.username.charAt(0).toUpperCase()}</div>
                          <span className="user-name">{u.username}</span>
                        </div>
                      </td>
                      <td className="text-muted">{u.email}</td>
                      <td>{u.firstName} {u.lastName}</td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                          <button
                            type="button"
                            onClick={() => !isAdmin && toggleUserStatus(u, !u.enabled)}
                            disabled={isAdmin || updatingStatusId === u.id}
                            title={isAdmin ? "Le statut de l'administrateur ne peut pas être modifié" : updatingStatusId === u.id ? "Mise à jour en cours..." : "Cliquez pour modifier le statut"}
                            style={{
                              position: 'relative',
                              display: 'inline-flex',
                              alignItems: 'center',
                              width: '46px',
                              height: '24px',
                              borderRadius: '12px',
                              border: 'none',
                              cursor: isAdmin || updatingStatusId === u.id ? 'not-allowed' : 'pointer',
                              background: u.enabled ? '#10b981' : '#cbd5e1',
                              boxShadow: u.enabled ? '0 0 10px rgba(16, 185, 129, 0.4)' : 'inset 0 1px 3px rgba(0,0,0,0.1)',
                              transition: 'all 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
                              opacity: updatingStatusId === u.id ? 0.6 : (isAdmin ? 0.8 : 1),
                              padding: '2px',
                              outline: 'none'
                            }}
                          >
                            <span
                              style={{
                                display: 'inline-block',
                                width: '20px',
                                height: '20px',
                                backgroundColor: '#fff',
                                borderRadius: '50%',
                                transform: u.enabled ? 'translateX(22px)' : 'translateX(0)',
                                transition: 'transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
                                boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
                              }}
                            />
                          </button>
                          <span style={{
                            fontSize: '13px',
                            fontWeight: 600,
                            minWidth: '50px',
                            textAlign: 'left',
                            color: u.enabled ? 'var(--text-1)' : 'var(--text-3)',
                            transition: 'color 0.3s ease'
                          }}>
                            {u.enabled ? 'Actif' : 'Inactif'}
                          </span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div className="action-buttons">
                          <button className="btn btn--ghost btn--sm btn-pill" onClick={() => openEdit(u)}>Éditer</button>
                          <button
                            className={`btn btn--ghost btn--sm btn-pill btn--danger ${isDeleteDisabled ? 'btn--disabled' : ''}`}
                            disabled={isDeleteDisabled}
                            title={isAdmin ? "L'utilisateur administrateur ne peut pas être supprimé" : isLastUser ? "Impossible de supprimer : il doit rester au moins un utilisateur sur la plateforme" : "Supprimer l'utilisateur"}
                            onClick={() => !isDeleteDisabled && initiateDelete(u)}
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={5} className="admin-card__empty">
                      Aucun utilisateur trouvé.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && renderModal('Nouvel utilisateur', () => setShowCreate(false), handleCreate, (
        <>
          <div className="input-group">
            <label>Nom d'utilisateur *</label>
            <input
              type="text"
              className="prompt-input"
              required
              value={formData.username}
              onChange={e => {
                const val = e.target.value
                setFormData(f => {
                  const updated = { ...f, username: val }
                  if (!isEmailModified) {
                    const cleanPrefix = val.toLowerCase().trim().replace(/\s+/g, '.')
                    updated.email = cleanPrefix ? `${cleanPrefix}@claria.local` : ''
                  }
                  return updated
                })
              }}
            />
          </div>
          <div className="input-group">
            <label>Email * (généré automatiquement)</label>
            <input
              type="email"
              className="prompt-input"
              required
              value={formData.email}
              onChange={e => {
                setIsEmailModified(true)
                setFormData(f => ({ ...f, email: e.target.value }))
              }}
            />
          </div>
          <div className="input-row">
            <div className="input-group">
              <label>Prénom</label>
              <input type="text" className="prompt-input" value={formData.firstName} onChange={e => setFormData(f => ({ ...f, firstName: e.target.value }))} />
            </div>
            <div className="input-group">
              <label>Nom</label>
              <input type="text" className="prompt-input" value={formData.lastName} onChange={e => setFormData(f => ({ ...f, lastName: e.target.value }))} />
            </div>
          </div>
          <div className="input-group">
            <label>Mot de passe *</label>
            <input type="password" className="prompt-input" required value={formData.password} onChange={e => setFormData(f => ({ ...f, password: e.target.value }))} />
            {renderPasswordRules(formData.password)}
          </div>
        </>
      ), !isPwdValid)}

      {showEdit && (() => {
        const editingUser = users.find(u => u.id === showEdit)
        const isAdmin = editingUser && isAdminUser(editingUser)
        return renderModal('Éditer l\'utilisateur', () => setShowEdit(null), handleEdit, (
          <>
            <div className="input-group">
              <label>{isAdmin ? "Nom d'utilisateur (lecture seule)" : "Nom d'utilisateur *"}</label>
              <input
                type="text"
                className={`prompt-input ${isAdmin ? 'prompt-input--readonly' : ''}`}
                readOnly={isAdmin}
                required={!isAdmin}
                value={formData.username}
                onChange={e => !isAdmin && setFormData(f => ({ ...f, username: e.target.value }))}
              />
            </div>
            <div className="input-group">
              <label>Email *</label>
              <input
                type="email"
                className="prompt-input"
                required
                value={formData.email}
                onChange={e => setFormData(f => ({ ...f, email: e.target.value }))}
              />
            </div>
            <div className="input-row">
              <div className="input-group">
                <label>Prénom</label>
                <input type="text" className="prompt-input" value={formData.firstName} onChange={e => setFormData(f => ({ ...f, firstName: e.target.value }))} />
              </div>
              <div className="input-group">
                <label>Nom</label>
                <input type="text" className="prompt-input" value={formData.lastName} onChange={e => setFormData(f => ({ ...f, lastName: e.target.value }))} />
              </div>
            </div>
            <div className="input-group" style={{ marginTop: '4px' }}>
              <label>Statut *</label>
              <select
                className={`prompt-input ${isAdmin ? 'prompt-input--readonly' : ''}`}
                disabled={isAdmin}
                value={formData.enabled ? 'true' : 'false'}
                onChange={e => !isAdmin && setFormData(f => ({ ...f, enabled: e.target.value === 'true' }))}
              >
                <option value="true">Actif</option>
                <option value="false">Inactif</option>
              </select>
            </div>
            <div className="input-group" style={{ marginTop: '8px', paddingTop: '16px', borderTop: '1px dashed var(--border)' }}>
              <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Nouveau mot de passe</span>
              </label>
              <input
                type="password"
                className="prompt-input"
                required
                placeholder="Un nouveau mot de passe est obligatoire..."
                value={formData.password}
                onChange={e => setFormData(f => ({ ...f, password: e.target.value }))}
              />
              {renderPasswordRules(formData.password)}
            </div>
          </>
        ), !isPwdValid)
      })()}

      {userToDelete && createPortal(
        <div className="admin-modal-backdrop">
          <div className="admin-modal-panel" style={{ maxWidth: '420px' }}>
            <div className="admin-modal__header">
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-1)' }}>Confirmer la suppression</h3>
              <button type="button" className="btn btn--ghost btn--icon" onClick={() => setUserToDelete(null)}><IconX size={16} /></button>
            </div>
            <div className="admin-modal__body" style={{ padding: '20px 24px' }}>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-2)', lineHeight: 1.5 }}>
                Êtes-vous sûr de vouloir supprimer l'utilisateur <strong>{userToDelete.username}</strong> ? Cette action est irréversible.
              </p>
            </div>
            <div className="admin-modal__footer">
              <button type="button" className="btn btn--ghost" onClick={() => setUserToDelete(null)}>Annuler</button>
              <button
                type="button"
                className="btn btn--primary"
                style={{ background: 'var(--danger)', borderColor: 'var(--danger)', color: '#fff' }}
                onClick={confirmDelete}
              >
                Supprimer
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      <style>{`
        .admin-page {
          max-width: 1080px;
          margin: 0 auto;
          padding: 40px 24px;
        }
        .admin-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 32px;
        }
        .admin-header__title {
          font-size: 28px;
          font-weight: 700;
          color: var(--text-1);
          margin-bottom: 6px;
          letter-spacing: -0.02em;
        }
        .admin-header__sub {
          font-size: 15px;
          color: var(--text-2);
        }
        .shadow-glow {
          box-shadow: 0 4px 14px 0 rgba(37,99,235,0.39);
        }
        .shadow-glow:hover {
          box-shadow: 0 6px 20px rgba(37,99,235,0.45);
        }
        .admin-card {
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          box-shadow: var(--shadow-md);
          overflow: hidden;
          width: 100%;
        }
        .admin-card__empty {
          padding: 60px 40px;
          text-align: center;
          color: var(--text-3);
          min-height: 400px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        }
        .table-responsive {
          overflow-x: auto;
        }
        .admin-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
        }
        .admin-table th {
          padding: 16px 20px;
          font-size: 12px;
          font-weight: 700;
          color: var(--text-3);
          background: transparent;
          border-bottom: 1px solid var(--border);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .admin-table td {
          padding: 16px 20px;
          border-bottom: 1px solid var(--border);
          vertical-align: middle;
        }
        .admin-table tbody tr:hover {
          background: var(--surface-2);
        }
        .admin-table tbody tr:last-child td {
          border-bottom: none;
        }
        .user-cell {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .user-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: var(--blue-light);
          color: var(--blue);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 14px;
        }
        .user-name {
          font-weight: 500;
          color: var(--text-1);
        }
        .action-buttons {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .btn-pill {
          border-radius: 9999px !important;
        }
        .btn--danger {
          color: var(--danger) !important;
        }
        .btn--danger:hover {
          background: var(--danger-bg) !important;
          border-color: transparent !important;
        }
        .btn--disabled {
          opacity: 0.45 !important;
          cursor: not-allowed !important;
        }
        .btn--disabled:hover {
          background: transparent !important;
        }
        
        .admin-modal-backdrop {
          position: fixed;
          top: 0; right: 0; bottom: 0; left: 0;
          background: rgba(15, 23, 42, 0.45);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 16px;
          animation: fadeIn 0.2s ease both;
        }
        .admin-modal-panel {
          background: rgba(255, 255, 255, 0.98);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(15, 23, 42, 0.08);
          border-radius: 20px;
          box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.08);
          width: 100%;
          max-width: 480px;
          max-height: 90vh;
          overflow-y: auto;
          overflow-x: hidden;
          display: flex;
          flex-direction: column;
          box-sizing: border-box;
          animation: scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) both;
        }
        .admin-modal__header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 18px 24px;
          border-bottom: 1px solid var(--border);
          box-sizing: border-box;
        }
        .admin-modal__body {
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          box-sizing: border-box;
          overflow-x: hidden;
          width: 100%;
        }
        .admin-modal__footer {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          padding: 16px 24px;
          border-top: 1px solid var(--border);
          background: var(--surface-2);
          border-radius: 0 0 20px 20px;
          box-sizing: border-box;
        }
        .input-group { 
          display: flex; 
          flex-direction: column; 
          gap: 6px; 
          width: 100%;
          box-sizing: border-box;
        }
        .input-group label { 
          font-size: 13px; 
          font-weight: 600; 
          color: var(--text-1); 
        }
        .input-group input, .input-group .prompt-input {
          width: 100% !important;
          box-sizing: border-box !important;
          max-width: 100% !important;
        }
        .input-row { 
          display: flex; 
          gap: 12px; 
          margin-bottom: 0; 
          width: 100%;
          box-sizing: border-box;
        }
        .input-row > div { 
          flex: 1 1 0%; 
          min-width: 0;
          margin-bottom: 0; 
          box-sizing: border-box;
        }
        .prompt-input--disabled, .prompt-input--readonly { 
          background: var(--surface-3); 
          color: var(--text-2);
          cursor: default; 
          opacity: 0.85; 
        }
      `}</style>
    </div>
  )
}
