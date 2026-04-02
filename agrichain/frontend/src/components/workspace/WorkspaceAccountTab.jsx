export default function WorkspaceAccountTab({ overview, profileForm, setProfileForm, submitting, onSaveProfile }) {
  return (
    <div className="dashboard-grid dashboard-grid-wide">
      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Profile</p>
          <h3>Account settings</h3>
        </div>
        <div className="form-grid two-col-grid top-gap">
          <label className="field-stack" htmlFor="profile-name">
            Full name
            <input autoComplete="name" id="profile-name" name="name" value={profileForm.name} onChange={(event) => setProfileForm((current) => ({ ...current, name: event.target.value }))} />
          </label>
          <label className="field-stack" htmlFor="profile-village">
            Village or city
            <input autoComplete="address-level2" id="profile-village" name="village" value={profileForm.village} onChange={(event) => setProfileForm((current) => ({ ...current, village: event.target.value }))} />
          </label>
          <label className="field-stack" htmlFor="profile-language">
            Language
            <select id="profile-language" name="language" value={profileForm.language} onChange={(event) => setProfileForm((current) => ({ ...current, language: event.target.value }))}>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="kn">Kannada</option>
              <option value="te">Telugu</option>
            </select>
          </label>
          <label className="field-stack" htmlFor="profile-market-access">
            Market access
            <input disabled id="profile-market-access" value={overview.profile.market_label} />
          </label>
        </div>
        <div className="button-row top-gap">
          <button className="primary-button" disabled={submitting} onClick={onSaveProfile} type="button">Save profile</button>
        </div>
      </section>

      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Account identity</p>
          <h3>{overview.profile.user_type_label} account</h3>
        </div>
        <div className="info-list top-gap">
          <div className="info-row">Phone: {overview.profile.phone}</div>
          <div className="info-row">AgriChain ID: {overview.profile.id}</div>
          <div className="info-row">Wallet address: <span className="hash-block">{overview.profile.wallet_address || "Not issued yet"}</span></div>
          <div className="info-row">Reputation score: {overview.profile.reputation_score}</div>
          <div className="info-row">Member since: {overview.profile.created_at_display}</div>
        </div>
      </section>
    </div>
  );
}
