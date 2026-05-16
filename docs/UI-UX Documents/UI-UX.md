# Casa Segura — UI/UX Spec

> This document is written to be fed, section by section, into a design tool (v0, Figma AI, etc.) to generate the actual UI. Each screen section is self-contained and can be used as a single prompt.

## 1. Brand and tone

- **Name (working):** Casa Segura
- **Audience:** Salvadoran adults, mixed digital literacy, often using a midrange Android over 4G, often anxious about a real estate decision they're about to make.
- **Tone:** Calm, plain, trustworthy. Not playful. Not corporate. Not cyberpunk. Think credit union, not fintech startup.
- **Voice in copy:** Short sentences. Spanish. Second person ("tú", not "usted" — warmer for this audience). Never alarmist.

## 2. Visual system

**Color palette (warm trust, accessible contrast):**
- Background: `#FAF7F2` (warm off-white)
- Surface: `#FFFFFF`
- Text primary: `#1F1A14` (warm near-black)
- Text secondary: `#6B6258`
- Brand accent: `#0F766E` (deep teal — calm, institutional)
- Verdict green: `#15803D`
- Verdict yellow: `#CA8A04`
- Verdict red: `#B91C1C`
- Border: `#E7E2D9`

**Typography:**
- Display + body: Inter or system sans-serif
- Body size: 16px minimum (mobile readability)
- Line height: 1.5 minimum
- Headings: medium weight, not bold-bold

**Layout:**
- Mobile-first, single column, max-width 480px
- Generous vertical spacing (24-32px between blocks)
- Tap targets minimum 44px tall
- Loading states never feel frozen — always show progress text

**Component style:**
- Rounded corners (12px on cards, 8px on inputs/buttons)
- Soft shadows only on interactive cards
- Borders preferred over shadows for non-interactive surfaces

## 3. Screens

### Screen 1 — Landing

**Purpose:** Explain the product in 5 seconds and start Flow 1.

**Elements:**
- Logo + name top-left
- Hero headline: *"Antes de comprar tu casa, revísala."*
- Subtext: *"Sube una foto del proyecto. Te decimos si es legítimo."*
- Single primary button: *"Empezar"* (full width on mobile)
- Below the fold: small "¿Cómo funciona?" link, "Ver código en GitHub" link
- Footer: *"Esto no es asesoría legal."*

**v0 prompt:**
```
Build a mobile-first Next.js landing page for "Casa Segura", a tool to verify
real estate projects in El Salvador. Single column, max-width 480px.
Background #FAF7F2, primary text #1F1A14, accent #0F766E.
Hero with title "Antes de comprar tu casa, revísala." and subtitle
"Sube una foto del proyecto. Te decimos si es legítimo."
One primary button "Empezar" full width.
Below: small links "¿Cómo funciona?" and "Ver código en GitHub".
Footer disclaimer "Esto no es asesoría legal." in small muted text.
Use Tailwind. Inter font. Rounded-xl. No shadows on the hero card.
```

### Screen 2 — Flow 1: Upload billboard photo

**Purpose:** Capture a photo or upload one.

**Elements:**
- Step indicator: "Paso 1 de 2 · Verificar proyecto"
- Large dropzone card
- Two CTAs inside: "Tomar foto" (uses `capture="environment"`) and "Subir desde galería"
- Helper text below: *"Apunta al cartel del proyecto. Asegúrate de ver el nombre del desarrollador y el número de permiso."*
- Example image (small, expandable): what a good billboard photo looks like
- Back link to landing

### Screen 3 — Flow 1: Loading

**Purpose:** Reassure during the 5-15s wait.

**Elements:**
- Centered spinner or progress bar
- Rotating status text:
  - *"Leyendo el cartel..."*
  - *"Buscando al desarrollador..."*
  - *"Revisando registros públicos..."*
  - *"Preparando el resultado..."*
- Cancel link

### Screen 4 — Flow 1: Result

**Purpose:** Deliver verdict and unlock Flow 2 if green/yellow.

**Layout based on verdict:**

**Green:**
- Big green check icon
- Headline: *"Sin alertas públicas"*
- Subtext: *"No encontramos señales de fraude para este proyecto. Aún así, revisa el contrato antes de firmar."*
- Findings list (if any minor): collapsible
- Primary CTA: *"Ahora revisa el contrato"* → Flow 2
- Secondary: *"Verificar otro proyecto"*

**Yellow:**
- Yellow warning icon
- Headline: *"Hay algo que revisar"*
- Subtext: *"Encontramos señales que vale la pena verificar."*
- Findings list expanded by default
- Primary CTA: *"Revisar el contrato con cuidado"* → Flow 2
- Secondary: *"Verificar otro proyecto"*

**Red:**
- Red alert icon
- Headline: *"Procede con cuidado"*
- Subtext: *"Encontramos señales serias. Considera buscar asesoría antes de avanzar."*
- Findings list, prominent
- Primary CTA: *"Ver el contrato igual"* (still allow, but framed as user choice)
- Secondary: *"Verificar otro proyecto"*

**Finding component:**
- Icon (severity color)
- Short title (bold, one line)
- Plain explanation (one or two sentences)
- "Evidencia" expandable — shows the source text or URL

**Always at bottom:**
- Disclaimer card: *"Esto no es asesoría legal. Antes de firmar, consulta un abogado."*
- Share button: *"Compartir resultado"* (for sharing with family)

### Screen 5 — Flow 2: Contract upload

Same pattern as Screen 2 but for PDF. Step indicator: "Paso 2 de 2 · Revisar contrato". Helper text: *"Sube el contrato en PDF. Lo leemos y te marcamos lo riesgoso."*

If user lands here without a Flow 1 session: redirect to Screen 1 with a small banner *"Primero verifica el proyecto."*

### Screen 6 — Flow 2: Loading

Same shape as Screen 3, different text:
- *"Leyendo el contrato..."*
- *"Buscando cláusulas riesgosas..."*
- *"Comparando con el proyecto..."*

### Screen 7 — Flow 2: Result

Same verdict structure as Screen 4. Findings are contract-specific (no escrow, vague delivery, etc.). At the bottom there's a "Descargar resumen" button (PDF of findings) — generated client-side from the JSON, no server storage.

## 4. SMS / Email / Link delivery templates

**SMS report-ready message:**
> Casa Segura: análisis listo. Resultado [band] ([score]/10). Ver reporte: [link]. Esto no es asesoría legal. ID [public_short_id].

**Email subject:**
> Tu análisis de contrato — Casa Segura — [contract type]

**Email body summary:**
> Tu análisis está listo. Adjuntamos el PDF y también puedes abrir el reporte web aquí: [link]. Esto no es asesoría legal. Antes de firmar, consulta a un abogado.

**Web-link confirmation:**
> Tu reporte está listo y disponible por 30 días. Guarda este enlace: [link]. Esto no es asesoría legal.

**On contract sent without Flow 1:**
> Antes del contrato, mándame primero una foto del cartel del proyecto. Eso me ayuda a revisar mejor.

**On PDF received (Flow 1 done):**
> Recibí el contrato. Dame un minuto para revisarlo...

## 5. States to design

For both upload screens, design these states:

- **Empty** (no file selected)
- **File selected** (preview thumbnail + filename + remove button)
- **Uploading** (progress)
- **Error: file too big** ("El archivo es muy grande. Máximo 10 MB.")
- **Error: wrong type** ("Necesitamos una foto. Intenta de nuevo.")
- **Error: server** ("Algo falló. Intenta de nuevo en un momento.")

## 6. Accessibility

- All copy at 8th-grade reading level or below
- Color is never the only carrier of meaning — verdicts always have icons and text labels
- Tap targets ≥44px
- Forms work with screen readers (proper labels)
- Test on a 360px-wide viewport (entry-level Android)

## 7. Implementation notes

- Stack: Next.js 14 App Router, Tailwind, shadcn/ui components
- File upload via Server Actions (no separate upload endpoint)
- API calls go to BE via env-configured base URL
- Session cookie for Flow 1 → Flow 2 gate; mirrors the BE Redis session
- Deploy: Vercel
- No analytics that capture content. If any: Plausible (no cookies, no PII)
