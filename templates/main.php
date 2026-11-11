<?php declare(strict_types=1); ?>
<div id="passwords-otp-app" class="passwords-otp-ap0 passwords-otp-ap1" data-template-build="1.0.1">
  <main class="passwords-otp-ap0__panel">
    <header class="passwords-otp-ap0__header">
      <div><h2>Passwort OTP Code Generator</h2><p class="passwords-otp-ap0__subtitle">OTP-Codes aus deinen eigenen gespeicherten OTP-Passwörtern sowie aus den mit dir geteilten OTP-Passwörtern</p></div>
    </header>
    <p id="passwords-otp-ap1-status" class="passwords-otp-ap0__status" role="status" aria-live="polite">Sitzung wird gepr&uuml;ft &hellip;</p>
    <form id="passwords-otp-ap1-login" autocomplete="off" hidden>
      <div class="passwords-otp-ap1__field"><label for="passwords-otp-ap1-password">Passwords-Master-Schl&uuml;ssel</label>
        <input id="passwords-otp-ap1-password" type="password" minlength="12" maxlength="128" autocomplete="off" spellcheck="false" autocapitalize="off"></div>
      <div id="passwords-otp-ap1-token-area" hidden>
        <div class="passwords-otp-ap1__field"><label for="passwords-otp-ap1-provider">Zweiter Authentifizierungsfaktor</label><select id="passwords-otp-ap1-provider"></select></div>
        <div class="passwords-otp-ap1__field"><label for="passwords-otp-ap1-code">Best&auml;tigungscode</label><input id="passwords-otp-ap1-code" type="text" inputmode="numeric" maxlength="128" autocomplete="one-time-code" spellcheck="false"></div>
      </div>
      <button type="submit">Tresor entsperren</button>
    </form>
    <div class="passwords-otp-ap12__toolbar"><button id="passwords-otp-ap12-open" type="button" hidden aria-haspopup="dialog" aria-controls="passwords-otp-ap12-dialog" aria-describedby="passwords-otp-ap12-help">Neues OTP Passwort hinzufügen</button></div>
    <p id="passwords-otp-ap12-help" class="passwords-otp-ap12__help">Hier kann ein neuer OTP Eintrag zu deinen Passwörtern hinzugefügt werden. Er wird in der Passwords App gespeichert und kann über diese App auch verwaltet (gelöscht, verändert) und mit anderen NextCloud Benutzern geteilt werden.</p>
    <dialog id="passwords-otp-ap12-dialog" class="passwords-otp-ap12__dialog" aria-labelledby="passwords-otp-ap12-title" aria-describedby="passwords-otp-ap12-description">
      <form id="passwords-otp-ap12-form" autocomplete="off">
        <h3 id="passwords-otp-ap12-title">Neues OTP Passwort hinzufügen</h3>
        <p id="passwords-otp-ap12-description">Einen neuen Eintrag in Nextcloud Passwords erstellen. Das OTP-Datenfeld wird automatisch angelegt.</p>
        <div class="passwords-otp-ap12__field"><label for="passwords-otp-ap12-label">Bezeichnung *</label><input id="passwords-otp-ap12-label" name="label" type="text" required maxlength="160" autocomplete="off"></div>
        <div class="passwords-otp-ap12__field"><label for="passwords-otp-ap12-username">Benutzername (optional)</label><input id="passwords-otp-ap12-username" name="username" type="text" maxlength="160" autocomplete="off" spellcheck="false"></div>
        <div class="passwords-otp-ap12__field"><label for="passwords-otp-ap12-password">Passwort *</label><input id="passwords-otp-ap12-password" name="password" type="password" required maxlength="4096" autocomplete="new-password" spellcheck="false" autocapitalize="off"><small>Passwort des Dienstkontos, nicht das Nextcloud-Masterpasswort.</small></div>
        <div class="passwords-otp-ap12__field"><label for="passwords-otp-ap12-secret">OTP-Secret (Base32) *</label><input id="passwords-otp-ap12-secret" name="secret" type="password" required maxlength="4096" autocomplete="off" spellcheck="false" autocapitalize="off"><small>Einrichtungsschl&uuml;ssel des Dienstes. Neuanlage: SHA-1, 6 Stellen, 30 Sekunden.</small></div>
        <p id="passwords-otp-ap12-feedback" class="passwords-otp-ap12__feedback" role="alert" aria-live="assertive"></p>
        <div class="passwords-otp-ap12__actions"><button id="passwords-otp-ap12-cancel" type="button">Abbrechen</button><button id="passwords-otp-ap12-save" type="submit">OTP speichern</button></div>
      </form>
    </dialog>
    <section id="passwords-otp-ap2-section" aria-label="Gefilterte TOTP-Konten" hidden>
      <label for="passwords-otp-ap2-search" class="passwords-otp-ap2__label">TOTP-Konten durchsuchen</label>
      <input id="passwords-otp-ap2-search" type="search" autocomplete="off" spellcheck="false" disabled placeholder="Titel, Benutzername oder Anbieter">
      <p id="passwords-otp-ap2-empty" role="status"></p><ul id="passwords-otp-ap2-list" class="passwords-otp-ap2__list"></ul>
      <p id="passwords-otp-ap3-feedback" role="status" aria-live="polite"></p>
    </section>
    <div class="passwords-otp-ap1__actions"><button id="passwords-otp-ap1-reload" type="button" hidden>Seite neu laden</button></div>
    <details class="passwords-otp-ap0__help"><summary>Sicherheit und Bedienung</summary>
      <p>TOTP-Codes werden lokal berechnet. Vor jedem neuen 30-Sekunden-Zeitfenster und bei R&uuml;ckkehr zum Tab pr&uuml;ft die App die urspr&uuml;ngliche Nextcloud-Anmeldung. Bereits angezeigte Codes k&ouml;nnen bis zur n&auml;chsten verpflichtenden Pr&uuml;fung sichtbar bleiben.</p>
      <p>Nach einem vollst&auml;ndigen App-Wechsel ist gegebenenfalls erneut der Master-Schl&uuml;ssel erforderlich. Neue Eintr&auml;ge werden nur nach ausdr&uuml;cklicher Best&auml;tigung erstellt. Bestehende Eintr&auml;ge werden &uuml;ber diese Oberfl&auml;che nicht ge&auml;ndert oder gel&ouml;scht. Kopierte Codes k&ouml;nnen in der Zwischenablagehistorie verbleiben.</p>
    </details>
  </main>
</div>
