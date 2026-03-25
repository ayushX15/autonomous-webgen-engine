# backend/tools/file_writer.py
# FIXED: next.config.js (not .ts) + hydration fixes + sanitizers

import os
import re
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / "secret.env")

OUTPUT_BASE_DIR = Path(
    os.getenv("GENERATED_OUTPUT_DIR", "./generated-output")
).resolve()


def create_run_directory() -> tuple[str, Path]:
    run_id  = f"run_{uuid.uuid4().hex[:8]}"
    run_dir = OUTPUT_BASE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "src" / "app").mkdir(parents=True, exist_ok=True)
    (run_dir / "src" / "components").mkdir(parents=True, exist_ok=True)
    (run_dir / "public").mkdir(parents=True, exist_ok=True)
    print(f"[File Writer] Created: {run_dir}")
    return run_id, run_dir


def _sanitize_page_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r'[\s_]+', '-', name)
    name = re.sub(r'[^a-z0-9\-]', '', name)
    name = re.sub(r'-page$', '', name)
    name = re.sub(r'-+', '-', name).strip('-')
    return name or "page"


def _clean_tsx_code(code: str) -> str:
    code = code.strip()

    # Remove markdown fences
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    code = code.strip()

    # Fix styled-jsx (causes client-only error)
    code = code.replace('<style jsx global>', '<style>')
    code = code.replace('<style jsx>', '<style>')
    code = re.sub(r'<style\s+jsx\b[^>]*>', '<style>', code)

    # Add suppressHydrationWarning to style tags (fixes hydration mismatch)
    code = re.sub(r'<style(\s*)>', '<style suppressHydrationWarning>', code)
    code = code.replace(
        'suppressHydrationWarning suppressHydrationWarning',
        'suppressHydrationWarning'
    )

    # Remove external CSS imports
    code = re.sub(r"import\s+styles\s+from\s+['\"].*?['\"].*?\n", "", code)
    code = re.sub(r"import\s+['\"].*?\.css['\"].*?\n", "", code)

    # Ensure 'use client' is first line
    lines = code.split("\n")
    lines = [l for l in lines if l.strip() not in (
        '"use client"', "'use client'",
        '"use client";', "'use client';",
    )]
    lines = ['"use client"'] + lines
    code = "\n".join(lines)

    # Fix multi-word function names
    def fix_fn(m):
        words = m.group(1).strip().split()
        return 'export default function ' + ''.join(w.capitalize() for w in words) + '('
    code = re.sub(r'export default function ([A-Za-z][A-Za-z0-9 ]*)\(', fix_fn, code)

    # Fix HTML entities
    code = code.replace("&#x27;", "'").replace("&#39;", "'")
    code = code.replace("&quot;", '"').replace("&amp;", "&")

    return code.strip()


def write_page(run_dir: Path, page_name: str, tsx_code: str, is_landing: bool) -> Path:
    clean = _sanitize_page_name(page_name)
    if is_landing or clean in ["index", "home", "landing", "landing-page"]:
        file_path = run_dir / "src" / "app" / "page.tsx"
    else:
        page_dir = run_dir / "src" / "app" / clean
        page_dir.mkdir(parents=True, exist_ok=True)
        file_path = page_dir / "page.tsx"

    file_path.write_text(_clean_tsx_code(tsx_code), encoding="utf-8")
    print(f"[File Writer] Written: {file_path.relative_to(run_dir)} ('{page_name}')")
    return file_path


def write_nextjs_config_files(run_dir: Path, color_palette: list[str]) -> None:
    p = color_palette[0] if color_palette else "#6366f1"
    s = color_palette[1] if len(color_palette) > 1 else "#0f172a"
    a = color_palette[2] if len(color_palette) > 2 else "#ffffff"

    # package.json
    (run_dir / "package.json").write_text(json.dumps({
        "name": "generated-site", "version": "0.1.0", "private": True,
        "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
        "dependencies": {"next": "14.2.3", "react": "^18.0.0", "react-dom": "^18.0.0"},
        "devDependencies": {
            "typescript": "^5.0.0", "@types/node": "^20.0.0",
            "@types/react": "^18.0.0", "@types/react-dom": "^18.0.0",
            "tailwindcss": "^3.4.0", "autoprefixer": "^10.4.0", "postcss": "^8.4.0"
        }
    }, indent=2), encoding="utf-8")

    # tsconfig.json
    (run_dir / "tsconfig.json").write_text(json.dumps({
        "compilerOptions": {
            "target": "es5", "lib": ["dom", "dom.iterable", "esnext"],
            "allowJs": True, "skipLibCheck": True, "strict": True,
            "noEmit": True, "esModuleInterop": True, "module": "esnext",
            "moduleResolution": "bundler", "resolveJsonModule": True,
            "isolatedModules": True, "jsx": "preserve", "incremental": True,
            "plugins": [{"name": "next"}], "paths": {"@/*": ["./src/*"]}
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"]
    }, indent=2), encoding="utf-8")

    # ─────────────────────────────────────────────────────────────────────────
    # CRITICAL FIX: next.config.JS not .ts
    # Next.js 14.2.3 does NOT support TypeScript config files
    # Using .ts causes: "Configuring Next.js via 'next.config.ts' is not supported"
    # ─────────────────────────────────────────────────────────────────────────
    (run_dir / "next.config.js").write_text(
        "/** @type {import('next').NextConfig} */\n"
        "const nextConfig = { reactStrictMode: false }\n"
        "module.exports = nextConfig\n",
        encoding="utf-8"
    )

    # tailwind.config.ts
    (run_dir / "tailwind.config.ts").write_text(f"""import type {{ Config }} from 'tailwindcss'
const config: Config = {{
  content: [
    './src/pages/**/*.{{js,ts,jsx,tsx,mdx}}',
    './src/components/**/*.{{js,ts,jsx,tsx,mdx}}',
    './src/app/**/*.{{js,ts,jsx,tsx,mdx}}',
  ],
  theme: {{ extend: {{ colors: {{ primary: '{p}', secondary: '{s}', accent: '{a}' }} }} }},
  plugins: [],
}}
export default config
""", encoding="utf-8")

    # postcss.config.mjs
    (run_dir / "postcss.config.mjs").write_text(
        "const config = { plugins: { tailwindcss: {}, autoprefixer: {} } }\nexport default config\n",
        encoding="utf-8"
    )

    # globals.css
    (run_dir / "src" / "app" / "globals.css").write_text(f"""@tailwind base;
@tailwind components;
@tailwind utilities;
:root {{ --primary:{p}; --secondary:{s}; --accent:{a}; }}
*{{ box-sizing:border-box; padding:0; margin:0; }}
html{{ scroll-behavior:smooth; }}
html,body{{ max-width:100vw; overflow-x:hidden; background:{s}; }}
::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-track{{background:{s}}}
::-webkit-scrollbar-thumb{{background:{p};border-radius:3px}}
""", encoding="utf-8")

    # layout.tsx
    (run_dir / "src" / "app" / "layout.tsx").write_text("""import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
const inter = Inter({ subsets: ['latin'], display: 'swap' })
export const metadata: Metadata = { title: 'Generated Site', description: 'AI Design Agent' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>{children}</body>
    </html>
  )
}
""", encoding="utf-8")

    print(f"[File Writer] Config files written to {run_dir.name}")


def write_all_pages(generated_pages: list, color_palette: list[str]) -> tuple[str, Path]:
    run_id, run_dir = create_run_directory()
    write_nextjs_config_files(run_dir, color_palette)
    for page in generated_pages:
        write_page(run_dir, page.page_name, page.tsx_code, page.is_landing)
    print(f"[File Writer] Done. generated-output/{run_id}/")
    return run_id, run_dir