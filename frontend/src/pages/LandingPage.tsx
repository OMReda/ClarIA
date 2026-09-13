import React, { useState, useEffect } from 'react'
import { useKeycloak } from '../auth/KeycloakProvider'
import { IconBarChart } from '../components/Icon'
import { Key, ShieldCheck, Zap } from 'lucide-react'

export const LandingPage: React.FC = () => {
  const { login } = useKeycloak()
  const [isRedirecting, setIsRedirecting] = useState(false)
  const [isEntering, setIsEntering] = useState(false)

  useEffect(() => {
    // Catch ALL Back button navigations in Chrome/Edge (popstate and pageshow regardless of event.persisted)
    const handleReturn = () => {
      setIsEntering(true)
      setIsRedirecting(false)
      setTimeout(() => setIsEntering(false), 400)
    }

    window.addEventListener('pageshow', handleReturn)
    window.addEventListener('popstate', handleReturn)

    return () => {
      window.removeEventListener('pageshow', handleReturn)
      window.removeEventListener('popstate', handleReturn)
    }
  }, [])

  if (isRedirecting) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100vh', width: '100%', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f1f5f9', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", WebkitFontSmoothing: 'antialiased', MozOsxFontSmoothing: 'grayscale' }}>
        <div className="spinner spinner--lg" />
        <div style={{ fontSize: '14px', fontWeight: 500, color: '#64748b', lineHeight: 1.6, letterSpacing: '0px', textAlign: 'center' }}>Redirection vers la connexion sécurisée...</div>
      </div>
    )
  }

  if (isEntering) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100vh', width: '100%', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f1f5f9', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", WebkitFontSmoothing: 'antialiased', MozOsxFontSmoothing: 'grayscale' }}>
        <div className="spinner spinner--lg" />
        <div style={{ fontSize: '14px', fontWeight: 500, color: '#64748b', lineHeight: 1.6, letterSpacing: '0px', textAlign: 'center' }}>Chargement de l'espace ClarIA...</div>
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
      backgroundColor: '#f1f5f9',
      backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)',
      backgroundSize: '32px 32px',
      fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Abstract Animated Ambient Orbs */}
      <div style={{
        position: 'absolute',
        top: '15%',
        left: '20%',
        width: '500px',
        height: '500px',
        background: 'rgba(37, 99, 235, 0.12)',
        filter: 'blur(100px)',
        borderRadius: '50%',
        animation: 'float 10s ease-in-out infinite alternate',
        zIndex: 0
      }} />
      <div style={{
        position: 'absolute',
        bottom: '15%',
        right: '20%',
        width: '600px',
        height: '600px',
        background: 'rgba(56, 189, 248, 0.08)',
        filter: 'blur(120px)',
        borderRadius: '50%',
        animation: 'float 12s ease-in-out infinite alternate-reverse',
        zIndex: 0
      }} />
      <style>
        {`
          @keyframes float {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(30px, -50px) scale(1.05); }
          }
        `}
      </style>

      {/* Main Glassmorphic Card */}
      <div style={{
        position: 'relative',
        zIndex: 10,
        background: 'rgba(255, 255, 255, 0.85)',
        backdropFilter: 'blur(32px)',
        WebkitBackdropFilter: 'blur(32px)',
        border: '1px solid rgba(255, 255, 255, 1)',
        borderRadius: '24px',
        padding: '56px 48px',
        width: '100%',
        maxWidth: '520px',
        boxShadow: '0 24px 48px -12px rgba(15,23,42,0.1), inset 0 1px 0 rgba(255,255,255,0.8)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        boxSizing: 'border-box'
      }}>
        {/* Brand Icon */}
        <div style={{ position: 'relative', marginBottom: '32px' }}>
          <div style={{
            position: 'absolute',
            inset: '-12px',
            background: 'rgba(37,99,235,0.3)',
            filter: 'blur(20px)',
            borderRadius: '50%'
          }} />
          <div style={{
            position: 'relative',
            width: '72px',
            height: '72px',
            background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
            borderRadius: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: '0 12px 24px -8px rgba(37,99,235,0.4), inset 0 1px 1px rgba(255,255,255,0.3)'
          }}>
            <IconBarChart size={36} strokeWidth={2.25} />
          </div>
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize: '32px',
          fontWeight: 700,
          color: '#0f172a',
          letterSpacing: '-0.03em',
          marginBottom: '16px',
          lineHeight: 1.2
        }}>
          ClarIA
        </h1>

        {/* Subtitle */}
        <p style={{
          fontSize: '16px',
          color: '#475569',
          marginBottom: '48px',
          lineHeight: 1.6,
          maxWidth: '380px'
        }}>
          Transformez vos données Excel et CSV en tableaux de bord intelligents grâce à l'IA.
        </p>

        {/* Login Button */}
        <button
          onClick={() => {
            setIsRedirecting(true)
            setTimeout(() => {
              try {
                login()
              } catch (e) {
                console.error("Login failed:", e)
                alert("Erreur de connexion Keycloak. Veuillez vérifier la console (F12).")
                setIsRedirecting(false)
              }
            }, 400)
          }}
          style={{
            width: '100%',
            height: '56px',
            background: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '14px',
            fontSize: '16px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
            boxShadow: '0 8px 16px -4px rgba(37,99,235,0.3), inset 0 1px 0 rgba(255,255,255,0.15)',
            cursor: 'pointer',
            fontFamily: 'inherit'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
            e.currentTarget.style.boxShadow = '0 12px 24px -6px rgba(37,99,235,0.4), inset 0 1px 0 rgba(255,255,255,0.15)';
            e.currentTarget.style.background = '#1d4ed8';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0) scale(1)';
            e.currentTarget.style.boxShadow = '0 8px 16px -4px rgba(37,99,235,0.3), inset 0 1px 0 rgba(255,255,255,0.15)';
            e.currentTarget.style.background = '#2563eb';
          }}
          onMouseDown={(e) => {
            e.currentTarget.style.transform = 'translateY(0) scale(0.98)';
          }}
        >
          Accéder à mon espace sécurisé
        </button>
      </div>

      {/* Trust Indicators - Minimalist Floating Footer outside the card */}
      <div style={{
        position: 'absolute',
        bottom: '36px',
        left: 0,
        right: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '24px',
        color: '#64748b',
        fontSize: '13px',
        fontWeight: 500,
        whiteSpace: 'nowrap',
        zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Key size={15} strokeWidth={2} style={{ color: '#94a3b8' }} />
          <span>Authentification SSO</span>
        </div>
        
        <span style={{ color: '#cbd5e1', fontSize: '12px' }}>•</span>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={15} strokeWidth={2} style={{ color: '#94a3b8' }} />
          <span>Connexion sécurisée</span>
        </div>
        
        <span style={{ color: '#cbd5e1', fontSize: '12px' }}>•</span>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={15} strokeWidth={2} style={{ color: '#94a3b8' }} />
          <span>Accès rapide</span>
        </div>
      </div>
    </div>
  )
}
