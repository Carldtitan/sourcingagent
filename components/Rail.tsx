"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Briefs" },
  { href: "/approvals", label: "Approvals", badge: true },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/specifications", label: "Specifications" },
  { href: "/mail", label: "Mail log" },
];

export function Rail({ waiting }: { waiting: number }) {
  const path = usePathname();

  return (
    <nav className="rail" aria-label="Sections">
      <Link className="wordmark" href="/">
        <b>AONIC</b>
        <span>Sourcing engine</span>
      </Link>

      <div className="rail-group">
        <span className="label">Work</span>
        {LINKS.map((link) => {
          const current =
            link.href === "/" ? path === "/" : path.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className="rail-link"
              aria-current={current ? "page" : undefined}
            >
              {link.label}
              {link.badge && waiting > 0 ? (
                <span className="tally" aria-label={`${waiting} waiting`}>
                  {waiting}
                </span>
              ) : null}
            </Link>
          );
        })}
      </div>

      <div className="rail-group" style={{ marginTop: "auto" }}>
        <span className="label">Every supplier here</span>
        <p
          style={{
            fontSize: 11.5,
            lineHeight: 1.45,
            padding: "0 20px",
            margin: 0,
          }}
        >
          is simulated. The email is real and reaches test inboxes only. No
          supplier outside this system is ever contacted.
        </p>
      </div>
    </nav>
  );
}
