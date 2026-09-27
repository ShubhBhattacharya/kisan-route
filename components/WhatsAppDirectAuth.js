'use client';

import React, { useState, useEffect, useRef } from 'react';

/**
 * WhatsAppDirectAuth Component
 * 100% Free, Zero-Third-Party WhatsApp Handshake Authentication (Method A: Kisan Screen Entry)
 *
 * Target Receiver Number: 918700257488
 */
export default function WhatsAppDirectAuth({ onLoginSuccess, onClose, defaultRole = 'farmer' }) {
  const [step, setStep] = useState('phone'); // 'phone' | 'verify'
  const [phone, setPhone] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState(defaultRole);
  const [generatedCode, setGeneratedCode] = useState('');
  const [enteredCode, setEnteredCode] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const inputRef = useRef(null);

  // Auto-focus code input when moving to step 2
  useEffect(() => {
    if (step === 'verify' && inputRef.current) {
      inputRef.current.focus();
    }
  }, [step]);

  // Clean 10-digit Indian phone
  const cleanPhoneNumber = (val) => {
    let digits = String(val || '').replace(/\D/g, '').replace(/^0+/, '');
    if (digits.length === 12 && digits.startsWith('91')) {
      digits = digits.slice(2);
    }
    return digits.length >= 10 ? digits.slice(-10) : digits;
  };

  // Step 1: Send WhatsApp Message & Open wa.me link
  const handleSendWhatsAppCode = () => {
    setErrorMsg('');
    const clean = cleanPhoneNumber(phone);

    if (!clean || clean.length !== 10) {
      setErrorMsg('कृपया 10 अंकों का मान्य मोबाइल नंबर दर्ज करें (e.g. 8700257488)');
      return;
    }

    // Generate random 4-digit numeric code (e.g., 6842)
    const code = Math.floor(1000 + Math.random() * 9000).toString();
    setGeneratedCode(code);
    setEnteredCode('');

    // WhatsApp Universal Link
    const receiverNumber = '918700257488';
    const message = `🌾 KisanRoute Login Request\nFarmer Mobile: ${clean}\nVerification Code: ${code}`;
    const waUrl = `https://wa.me/${receiverNumber}?text=${encodeURIComponent(message)}`;

    // Automatically open WhatsApp in new tab / app
    if (typeof window !== 'undefined') {
      window.open(waUrl, '_blank', 'noopener,noreferrer');
    }

    // Advance to Step 2
    setStep('verify');
  };

  // Step 2: Confirm entered code against generated code
  const handleConfirmCode = async (e) => {
    if (e) e.preventDefault();
    setErrorMsg('');

    const cleanInput = enteredCode.trim();

    if (!cleanInput || cleanInput.length !== 4) {
      setErrorMsg('कृपया स्क्रीन पर दिखाया गया 4 अंकों का कोड दर्ज करें।');
      return;
    }

    if (cleanInput !== generatedCode) {
      setErrorMsg('❌ Galat Code! Kripya screen par dikha code enter karein.');
      return;
    }

    setLoading(true);
    const cleanPhone = cleanPhoneNumber(phone);

    // Save session to localStorage
    const sessionData = {
      phone: cleanPhone,
      role: role,
      fullName: fullName || `${role.charAt(0).toUpperCase() + role.slice(1)} ${cleanPhone.slice(-4)}`,
      isLoggedIn: true,
      authMethod: 'whatsapp_handshake',
      verifiedAt: new Date().toISOString()
    };

    if (typeof window !== 'undefined') {
      localStorage.setItem('kr_user', JSON.stringify(sessionData));
    }

    // Attempt server session creation if API endpoint is available
    try {
      await fetch('/api/auth/phone-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: cleanPhone,
          role: role,
          full_name: sessionData.fullName,
          otp_verified: true
        })
      });
    } catch (err) {
      console.log('[WhatsAppDirectAuth] Local session established.');
    }

    setLoading(false);

    // Trigger onLoginSuccess callback
    if (onLoginSuccess) {
      onLoginSuccess(sessionData);
    } else if (typeof window !== 'undefined') {
      // Default redirect to role dashboard
      window.location.href = `/${role}/dashboard`;
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modalCard}>
        {/* Header */}
        <div style={styles.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '26px' }}>💬</span>
            <div>
              <h3 style={styles.title}>WhatsApp Login (व्हाट्सएप लॉगिन)</h3>
              <span style={styles.badge}>⚡ 100% Free • Direct Handshake</span>
            </div>
          </div>
          {onClose && (
            <button type="button" onClick={onClose} style={styles.closeBtn} aria-label="Close">
              &times;
            </button>
          )}
        </div>

        {/* Body */}
        <div style={styles.body}>
          {/* Role Pills */}
          <div style={{ marginBottom: '14px' }}>
            <label style={styles.label}>भूमिका चुनें / Select Role:</label>
            <div style={styles.roleContainer}>
              {[
                { id: 'farmer', label: '🌾 किसान (Farmer)' },
                { id: 'driver', label: '🚚 चालक (Driver)' },
                { id: 'cluster', label: '🤝 समूह (Cluster)' },
                { id: 'customer', label: '🛒 खरीदार (Buyer)' },
                { id: 'wholesaler', label: '🏬 आढ़ती (Wholesaler)' }
              ].map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setRole(r.id)}
                  style={{
                    ...styles.roleChip,
                    ...(role === r.id ? styles.roleChipActive : {})
                  }}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div style={styles.errorBanner}>
              {errorMsg}
            </div>
          )}

          {/* STEP 1: Phone Input */}
          {step === 'phone' && (
            <div>
              <div style={{ marginBottom: '12px' }}>
                <label style={styles.label}>मोबाइल नंबर / Mobile Number:</label>
                <div style={styles.phoneInputWrapper}>
                  <span style={styles.countryCode}>🇮🇳 +91</span>
                  <input
                    type="tel"
                    value={phone}
                    maxLength={10}
                    placeholder="8700257488"
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendWhatsAppCode()}
                    style={styles.phoneInput}
                  />
                </div>
                <span style={styles.hintText}>
                  10 अंकों का किसान मोबाइल नंबर दर्ज करें (10-digit number)
                </span>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={styles.label}>
                  पूरा नाम / Full Name <span style={{ color: '#64748b', fontWeight: 'normal' }}>(वैकल्पिक)</span>:
                </label>
                <input
                  type="text"
                  value={fullName}
                  placeholder="e.g. Ramesh Patel"
                  onChange={(e) => setFullName(e.target.value)}
                  style={styles.textInput}
                />
              </div>

              <button
                type="button"
                onClick={handleSendWhatsAppCode}
                style={styles.whatsappBtn}
              >
                <span style={{ fontSize: '18px' }}>💬</span>
                <span>WhatsApp Par Code Bhejo</span>
              </button>
            </div>
          )}

          {/* STEP 2: Screen Code Verification */}
          {step === 'verify' && (
            <div>
              {/* Prominent Code Display */}
              <div style={styles.codeCard}>
                <div style={{ fontSize: '12px', color: '#166534', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Aapka 4-Digit Verification Code:
                </div>
                <div style={styles.prominentCode}>
                  {generatedCode}
                </div>
                <div style={styles.instructionsText}>
                  <strong>निर्देश / Instructions:</strong>
                  <br />
                  1. WhatsApp par ye message send karein.
                  <br />
                  2. Wahi 4-digit code yahan enter karke confirm karein.
                </div>
              </div>

              {/* Code Input */}
              <div style={{ marginBottom: '14px' }}>
                <label style={{ ...styles.label, textAlign: 'center', display: 'block' }}>
                  Yahan 4-digit code enter karein:
                </label>
                <input
                  ref={inputRef}
                  type="text"
                  maxLength={4}
                  value={enteredCode}
                  placeholder="••••"
                  inputMode="numeric"
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '').slice(0, 4);
                    setEnteredCode(val);
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleConfirmCode()}
                  style={styles.codeInput}
                />
              </div>

              <button
                type="button"
                onClick={handleConfirmCode}
                disabled={loading}
                style={styles.confirmBtn}
              >
                <span>{loading ? '⏳' : '✅'}</span>
                <span>{loading ? 'Logging in...' : 'Confirm & Login'}</span>
              </button>

              <div style={{ textAlign: 'center', marginTop: '14px' }}>
                <button
                  type="button"
                  onClick={() => {
                    setStep('phone');
                    setErrorMsg('');
                  }}
                  style={styles.resendLink}
                >
                  🔄 Resend / Change Number (नंबर बदलें)
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <span>🔒 Direct WhatsApp Handshake</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <span>🌾</span> 0% Middlemen
          </span>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.65)',
    backdropFilter: 'blur(4px)',
    zIndex: 99999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '16px',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
  },
  modalCard: {
    background: '#ffffff',
    borderRadius: '16px',
    maxWidth: '430px',
    width: '100%',
    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.25)',
    overflow: 'hidden'
  },
  header: {
    padding: '16px 20px',
    background: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  title: {
    margin: 0,
    fontSize: '17px',
    fontWeight: '800',
    color: '#1b5e20'
  },
  badge: {
    fontSize: '11px',
    color: '#166534',
    fontWeight: '700',
    background: '#ecfdf5',
    padding: '2px 8px',
    borderRadius: '999px',
    border: '1px solid #86efac',
    display: 'inline-block',
    marginTop: '2px'
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: '26px',
    lineHeight: 1,
    color: '#94a3b8',
    cursor: 'pointer',
    padding: '0 4px'
  },
  body: {
    padding: '20px'
  },
  label: {
    display: 'block',
    fontSize: '12.5px',
    fontWeight: '700',
    color: '#374151',
    marginBottom: '6px'
  },
  roleContainer: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap'
  },
  roleChip: {
    background: '#f1f5f9',
    border: '1.5px solid #e2e8f0',
    color: '#475569',
    borderRadius: '999px',
    padding: '5px 12px',
    fontSize: '11.5px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'all 0.15s ease'
  },
  roleChipActive: {
    background: '#ecfdf5',
    borderColor: '#10b981',
    color: '#065f46',
    boxShadow: '0 2px 6px rgba(16,185,129,0.2)'
  },
  errorBanner: {
    background: '#fef2f2',
    color: '#991b1b',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    padding: '10px 14px',
    fontSize: '12.5px',
    marginBottom: '14px',
    lineHeight: 1.4
  },
  phoneInputWrapper: {
    display: 'flex',
    alignItems: 'center',
    border: '1.5px solid #cbd5e1',
    borderRadius: '10px',
    background: '#ffffff',
    overflow: 'hidden'
  },
  countryCode: {
    background: '#f1f5f9',
    padding: '10px 12px',
    fontSize: '14px',
    fontWeight: '700',
    color: '#334155',
    borderRight: '1px solid #cbd5e1'
  },
  phoneInput: {
    border: 'none',
    outline: 'none',
    padding: '10px 14px',
    fontSize: '15px',
    fontWeight: '600',
    width: '100%',
    letterSpacing: '0.5px'
  },
  textInput: {
    width: '100%',
    boxSizing: 'border-box',
    border: '1.5px solid #cbd5e1',
    borderRadius: '10px',
    padding: '10px 14px',
    fontSize: '14px',
    outline: 'none'
  },
  hintText: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '4px',
    display: 'block'
  },
  whatsappBtn: {
    width: '100%',
    background: 'linear-gradient(135deg, #25D366 0%, #128C7E 100%)',
    color: '#ffffff',
    border: 'none',
    padding: '12px 16px',
    borderRadius: '10px',
    fontSize: '14.5px',
    fontWeight: '800',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    boxShadow: '0 4px 12px rgba(37,211,102,0.35)',
    transition: 'all 0.2s ease'
  },
  codeCard: {
    background: '#f0fdf4',
    border: '2px solid #86efac',
    borderRadius: '12px',
    padding: '14px',
    textAlign: 'center',
    marginBottom: '16px'
  },
  prominentCode: {
    fontSize: '34px',
    fontWeight: '900',
    letterSpacing: '6px',
    color: '#15803d',
    padding: '6px 0',
    fontFamily: 'monospace'
  },
  instructionsText: {
    fontSize: '12.5px',
    color: '#166534',
    lineHeight: 1.5,
    marginTop: '6px',
    borderTop: '1px dashed #bbf7d0',
    paddingTop: '8px'
  },
  codeInput: {
    width: '100%',
    boxSizing: 'border-box',
    border: '2px solid #10b981',
    borderRadius: '12px',
    padding: '12px',
    fontSize: '26px',
    fontWeight: '800',
    letterSpacing: '8px',
    textAlign: 'center',
    outline: 'none',
    background: '#ffffff'
  },
  confirmBtn: {
    width: '100%',
    background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
    color: '#ffffff',
    border: 'none',
    padding: '12px',
    borderRadius: '10px',
    fontSize: '14.5px',
    fontWeight: '800',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    boxShadow: '0 4px 12px rgba(16,185,129,0.3)',
    transition: 'all 0.2s ease'
  },
  resendLink: {
    background: 'none',
    border: 'none',
    color: '#059669',
    fontWeight: '700',
    fontSize: '12.5px',
    cursor: 'pointer',
    textDecoration: 'underline'
  },
  footer: {
    padding: '12px 20px',
    background: '#f8fafc',
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: '11.5px',
    color: '#64748b'
  }
};
