import { Link } from "react-router-dom";

const ROLE_OPTIONS = [{ value: "farmer", label: "Farmer" }, { value: "buyer", label: "Buyer" }];
const MARKET_OPTIONS = [{ value: "local", label: "Local" }, { value: "global", label: "Global" }, { value: "both", label: "Both" }];

export default function AccessPanel({
  mode,
  setMode,
  phone,
  setPhone,
  phoneError,
  registerForm,
  onRegisterField,
  submitting,
  submitRegister,
  otpRequested,
  requestOtp,
  otp,
  setOtp,
  otpError,
  verifyOtp,
}) {
  return (
    <div className="auth-card auth-form-card auth-form-card-wide">
      <div className="stack-list">
        <p className="eyebrow">Secure access</p>
        <h2>{mode === "register" ? "Create your KrishiBlock account" : "Sign in with OTP"}</h2>
        <p className="support-copy">Use the same profile across the workspace, wallet, verification pages, and WhatsApp simulation.</p>
      </div>

      <div className="segmented-control top-gap" role="tablist" aria-label="Access mode">
        <button aria-selected={mode === "register"} className={mode === "register" ? "segment active" : "segment"} onClick={() => setMode("register")} role="tab" type="button">Create account</button>
        <button aria-selected={mode === "login"} className={mode === "login" ? "segment active" : "segment"} onClick={() => setMode("login")} role="tab" type="button">Sign in</button>
      </div>

      <label className="field-stack top-gap" htmlFor="access-phone">
        Phone number
        <input
          autoComplete="tel"
          id="access-phone"
          inputMode="tel"
          name="phone"
          onChange={(event) => setPhone(event.target.value)}
          placeholder="+919876543210"
          spellCheck={false}
          type="tel"
          value={phone}
        />
        {phoneError ? <small className="field-error">{phoneError}</small> : null}
      </label>

      {mode === "register" ? (
        <div className="stack-list top-gap">
          <label className="field-stack" htmlFor="register-name">
            Full name
            <input autoComplete="name" id="register-name" name="name" onChange={(event) => onRegisterField("name", event.target.value)} placeholder="Ramesh Gowda" value={registerForm.name} />
          </label>
          <label className="field-stack" htmlFor="register-village">
            Village or city
            <input autoComplete="address-level2" id="register-village" name="village" onChange={(event) => onRegisterField("village", event.target.value)} placeholder="Mandya" value={registerForm.village} />
          </label>
          <div className="form-grid two-col-grid">
            <label className="field-stack" htmlFor="register-role">
              Role
              <select id="register-role" name="user_type" onChange={(event) => onRegisterField("user_type", event.target.value)} value={registerForm.user_type}>
                {ROLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="field-stack" htmlFor="register-market">
              Market preference
              <select id="register-market" name="market_type" onChange={(event) => onRegisterField("market_type", event.target.value)} value={registerForm.market_type}>
                {MARKET_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
          </div>
          <label className="field-stack" htmlFor="register-language">
            Language
            <select id="register-language" name="language" onChange={(event) => onRegisterField("language", event.target.value)} value={registerForm.language}>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="kn">Kannada</option>
              <option value="te">Telugu</option>
            </select>
          </label>
          <button className="primary-button" disabled={submitting || Boolean(phoneError)} onClick={submitRegister} type="button">{submitting ? "Creating account..." : "Create account"}</button>
        </div>
      ) : (
        <div className="stack-list top-gap">
          {!otpRequested ? (
            <button className="primary-button" disabled={submitting || Boolean(phoneError)} onClick={requestOtp} type="button">{submitting ? "Sending OTP..." : "Request OTP"}</button>
          ) : (
            <>
              <label className="field-stack" htmlFor="access-otp">
                Enter OTP
                <input
                  autoComplete="one-time-code"
                  id="access-otp"
                  inputMode="numeric"
                  name="otp"
                  onChange={(event) => setOtp(event.target.value)}
                  placeholder="6-digit code"
                  spellCheck={false}
                  type="text"
                  value={otp}
                />
                {otpError ? <small className="field-error">{otpError}</small> : null}
              </label>
              <div className="button-row">
                <button className="primary-button" disabled={submitting || Boolean(phoneError || otpError)} onClick={verifyOtp} type="button">{submitting ? "Verifying..." : "Sign in"}</button>
                <button className="ghost-button" disabled={submitting} onClick={requestOtp} type="button">Resend OTP</button>
              </div>
            </>
          )}
          <small className="mini-note">Existing users sign in with OTP. New users create the account directly from this page.</small>
        </div>
      )}

      <div className="auth-footer-links top-gap">
        <Link className="ghost-button" to="/market">Browse listings</Link>
        <Link className="ghost-button" to="/bot">Open WhatsApp sim</Link>
      </div>
    </div>
  );
}
