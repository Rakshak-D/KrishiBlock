export default function WorkspaceAccountTab({ overview, profileForm, setProfileForm, submitting, onSaveProfile }) {
  return (
    <div className="dashboard-grid dashboard-grid-wide">
      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Profile</p>
          <h3>Account settings</h3>
        </div>
        <div className="form-grid two-col-grid top-gap">
          <label className="field-stack">
            Full name
            <input value={profileForm.name} onChange={(event) => setProfileForm((current) => ({ ...current, name: event.target.value }))} />
          </label>
          <label className="field-stack">
            Village or city
            <input value={profileForm.village} onChange={(event) => setProfileForm((current) => ({ ...current, village: event.target.value }))} />
          </label>
          <label className="field-stack">
            Language
            <select value={profileForm.language} onChange={(event) => setProfileForm((current) => ({ ...current, language: event.target.value }))}>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="kn">Kannada</option>
              <option value="te">Telugu</option>
            </select>
          </label>
          <label className="field-stack">
            Market access
            <input disabled value={overview.profile.market_label} />
          </label>
        </div>
        <div className="button-row top-gap">
          <button className="primary-button" disabled={submitting} onClick={onSaveProfile} type="button">Save profile</button>
        </div>
      </section>

      <section className="detail-card compact-panel">
        <div className="section-title">
          <p className="eyebrow">Workspace identity</p>
          <h3>{overview.profile.user_type_label} account</h3>
        </div>
        <div className="info-list top-gap">
          <div className="info-row">Phone: {overview.profile.phone}</div>
          <div className="info-row">AgriChain ID: {overview.profile.id}</div>
          <div className="info-row">Reputation score: {overview.profile.reputation_score}</div>
          <div className="info-row">Member since: {overview.profile.created_at_display}</div>
        </div>
        <div className="mini-note top-gap">Notifications in the overview tab are generated from your real listings, wallet, and order state.</div>
      </section>
    </div>
  );
}
