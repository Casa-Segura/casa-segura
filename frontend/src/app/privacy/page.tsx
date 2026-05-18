import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";
import { PUBLIC_SOURCE_REPO_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Política de privacidad · Casa Segura",
  description:
    "Qué datos procesa Casa Segura, cómo se usan los canales de entrega y cómo ejercer tus derechos.",
};

export default function PrivacyPage() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-[var(--spacing-section)]">
        <header className="shrink-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">
            <span translate="no">Casa Segura</span>
          </p>
        </header>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex min-w-0 flex-1 flex-col gap-6 rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm outline-none"
        >
          <div className="flex flex-col gap-2">
            <h1 className="text-balance text-[1.625rem] font-semibold leading-snug tracking-tight text-text-primary sm:text-3xl">
              Política de privacidad
            </h1>
            <p className="text-sm text-text-secondary">
              Versión resumida para personas usuarias. Última actualización:
              mayo de 2026.
            </p>
          </div>

          <div className="space-y-6 text-base leading-relaxed text-text-secondary">
            <section className="space-y-3" aria-labelledby="privacy-purpose">
              <h2
                id="privacy-purpose"
                className="text-lg font-semibold text-text-primary"
              >
                Finalidad
              </h2>
              <p>
                <span translate="no">Casa Segura</span> analiza el texto de
                contratos inmobiliarios que vos subís para generar un informe
                orientativo. {DISCLAIMER_SHORT}: el informe no sustituye la
                revisión de un abogado.
              </p>
            </section>

            <section className="space-y-3" aria-labelledby="privacy-data">
              <h2
                id="privacy-data"
                className="text-lg font-semibold text-text-primary"
              >
                Datos que podemos procesar
              </h2>
              <ul className="list-disc space-y-2 pl-5">
                <li>
                  Contenido que envías en el flujo web (por ejemplo PDF o
                  imágenes del contrato) para ejecutar el análisis solicitado.
                </li>
                <li>
                  Datos de contacto que elijas para la entrega del informe
                  (correo o número de teléfono), solo para enviar el enlace o
                  mensaje acordado.
                </li>
                <li>
                  Metadatos técnicos mínimos que tu navegador y la
                  infraestructura generan de forma habitual (por ejemplo
                  dirección IP en registros del servidor), según cómo esté
                  desplegado el backend.
                </li>
              </ul>
              <p>
                No vendemos tus datos personales. El producto está pensado para
                minimizar lo que se conserva; los plazos exactos de retención
                dependen de la configuración operativa del backend documentada
                en el código y en las decisiones de despliegue del equipo.
              </p>
            </section>

            <section className="space-y-3" aria-labelledby="privacy-channels">
              <h2
                id="privacy-channels"
                className="text-lg font-semibold text-text-primary"
              >
                SMS, correo y otros canales
              </h2>
              <p>
                Si elegís recibir el resultado por SMS, correo u otro proveedor,
                ese canal procesa la entrega según sus propias condiciones.
                Nosotros usamos el destinatario solo para completar el envío que
                pedís; no usamos esos mensajes para entrenar modelos propios.
              </p>
            </section>

            <section className="space-y-3" aria-labelledby="privacy-rights">
              <h2
                id="privacy-rights"
                className="text-lg font-semibold text-text-primary"
              >
                Tus derechos y contacto
              </h2>
              <p>
                Para solicitudes sobre datos personales (acceso, rectificación,
                supresión cuando aplique), abrí un issue en el repositorio
                público o contactá al mantenedor del despliegue que estés
                usando.
              </p>
              <p>
                <span className="font-medium text-text-primary">
                  Código abierto:
                </span>{" "}
                <a
                  href={PUBLIC_SOURCE_REPO_URL}
                  className="font-medium text-accent underline underline-offset-4 hover:opacity-90 focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  rel="noopener noreferrer"
                >
                  <span translate="no">Casa Segura Repository</span>
                </a>
              </p>
            </section>
          </div>

          <p className="border-t border-border pt-6 text-sm leading-snug text-text-secondary">
            <Link
              href="/"
              className="font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Volver al inicio
            </Link>
          </p>
        </main>

        <footer className="mt-auto shrink-0 border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
