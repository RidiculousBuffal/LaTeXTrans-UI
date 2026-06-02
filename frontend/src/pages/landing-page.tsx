import {useEffect, useRef, useState} from "react"
import {Link, useNavigate} from "react-router-dom"
import {useTheme} from "next-themes"
import {
    ArrowRightIcon,
    BookOpenIcon,
    MoonIcon,
    SunIcon,
    CheckCircle2Icon,
    SparklesIcon,
    GitFork
} from "lucide-react"
import {Button} from "@/components/ui/button"
import {useAuth} from "@/lib/auth-context"
import {cn} from "@/lib/utils"

// Floating LaTeX symbols for the hero background
const LATEX_SYMBOLS = [
    "\\int", "\\sum", "\\prod", "\\nabla", "\\partial", "\\infty",
    "\\alpha", "\\beta", "\\gamma", "\\delta", "\\lambda", "\\sigma",
    "\\forall", "\\exists", "\\in", "\\subset", "\\cup", "\\cap",
    "\\mathbb{R}", "\\mathcal{L}", "\\hat{\\theta}", "\\vec{v}",
    "E=mc^2", "F=ma", "\\ell", "\\hbar", "\\Omega", "\\Phi",
]

function FloatingSymbol({symbol, style}: { symbol: string; style: React.CSSProperties }) {
    return (
        <span
            className="absolute select-none font-mono text-primary/10 dark:text-primary/8 pointer-events-none"
            style={style}
        >
      {symbol}
    </span>
    )
}

function HeroBackground() {
    const items = useRef(
        LATEX_SYMBOLS.map((sym, i) => ({
            sym,
            left: `${(i * 37 + 5) % 95}%`,
            top: `${(i * 53 + 8) % 90}%`,
            fontSize: `${0.7 + (i % 5) * 0.25}rem`,
            animationDelay: `${(i * 0.4) % 6}s`,
            animationDuration: `${12 + (i % 8) * 2}s`,
        }))
    ).current

    return (
        <div className="absolute inset-0 overflow-hidden" aria-hidden>
            {items.map((item, i) => (
                <FloatingSymbol
                    key={i}
                    symbol={item.sym}
                    style={{
                        left: item.left,
                        top: item.top,
                        fontSize: item.fontSize,
                        animation: `float ${item.animationDuration} ease-in-out ${item.animationDelay} infinite`,
                    }}
                />
            ))}
        </div>
    )
}


export default function LandingPage() {
    const {resolvedTheme, setTheme} = useTheme()
    const {user, isLoading, registrationEnabled} = useAuth()
    const navigate = useNavigate()
    const [scrolled, setScrolled] = useState(false)

    useEffect(() => {
        if (!isLoading && user) {
            navigate("/", {replace: true})
        }
    }, [user, isLoading, navigate])

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 20)
        window.addEventListener("scroll", onScroll, {passive: true})
        return () => window.removeEventListener("scroll", onScroll)
    }, [])

    return (
        <div className="min-h-svh bg-background text-foreground">
            {/* Floating animation keyframes */}
            <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0.6; }
          33% { transform: translateY(-18px) rotate(3deg); opacity: 1; }
          66% { transform: translateY(10px) rotate(-2deg); opacity: 0.7; }
        }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes fade-up {
          from { opacity: 0; transform: translateY(24px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-up { animation: fade-up 0.7s ease-out both; }
        .animate-fade-up-d1 { animation: fade-up 0.7s 0.15s ease-out both; }
        .animate-fade-up-d2 { animation: fade-up 0.7s 0.3s ease-out both; }
        .animate-fade-up-d3 { animation: fade-up 0.7s 0.45s ease-out both; }
        .shimmer-text {
          background: linear-gradient(90deg, var(--color-primary) 0%, oklch(0.75 0.18 240) 30%, oklch(0.65 0.22 280) 50%, oklch(0.75 0.18 240) 70%, var(--color-primary) 100%);
          background-size: 200% auto;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          animation: shimmer 4s linear infinite;
        }
      `}</style>

            {/* Navbar */}
            <header
                className={cn(
                    "fixed top-0 inset-x-0 z-50 transition-all duration-300",
                    scrolled
                        ? "bg-background/80 backdrop-blur-xl border-b border-border/60 shadow-sm"
                        : "bg-transparent"
                )}
            >
                <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-2">
                        <div
                            className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
                            L
                        </div>
                        <span className="font-semibold tracking-tight">LaTeXTrans</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
                            aria-label="Toggle theme"
                        >
                            {resolvedTheme === "dark" ? <SunIcon className="h-4 w-4"/> :
                                <MoonIcon className="h-4 w-4"/>}
                        </Button>
                        <Button variant="ghost" size="sm" asChild>
                            <Link to="/login">登录</Link>
                        </Button>
                        {registrationEnabled && (
                            <Button size="sm" asChild>
                                <Link to="/register">
                                    免费注册
                                    <ArrowRightIcon className="ml-1 h-3.5 w-3.5"/>
                                </Link>
                            </Button>
                        )}
                    </div>
                </div>
            </header>

            {/* Hero */}
            <section
                className="relative flex min-h-svh flex-col items-center justify-center overflow-hidden px-6 pt-20">
                {/* Gradient blobs */}
                <div className="absolute inset-0 pointer-events-none" aria-hidden>
                    <div
                        className="absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full bg-primary/10 blur-[120px]"/>
                    <div
                        className="absolute -bottom-20 -right-20 h-[500px] w-[500px] rounded-full bg-violet-500/8 blur-[100px]"/>
                    <div
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[400px] w-[800px] rounded-full bg-cyan-500/5 blur-[80px]"/>
                </div>

                <HeroBackground/>

                <div className="relative z-10 mx-auto max-w-4xl text-center">
                    <div
                        className="animate-fade-up mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-background/60 px-4 py-1.5 text-sm backdrop-blur">
                        <SparklesIcon className="h-3.5 w-3.5 text-primary"/>
                        <span className="text-muted-foreground">Agent · BabelDoc</span>
                    </div>

                    <h1 className="animate-fade-up-d1 font-heading text-5xl font-bold leading-[1.1] tracking-tight sm:text-6xl lg:text-7xl">
                        LatexTrans
                    </h1>

                    <div className="animate-fade-up-d2 mx-auto mt-6 max-w-2xl text-lg text-muted-foreground leading-relaxed flex justify-center content-center gap-2.5">
                        <GitFork/> <a target="_blank" href={"https://github.com/NiuTrans/LaTeXTrans"}>NiuTrans/LaTeXTrans</a> <a target="_blank" href={"https://github.com/RidiculousBuffal/LaTeXTrans-UI"}>RidiculousBuffal/LaTeXTrans-UI</a>
                    </div>

                    <div className="animate-fade-up-d3 mt-10 flex flex-wrap items-center justify-center gap-3">
                        <Button size="lg" variant="outline" className="h-12 px-8 text-base" asChild>
                            <Link to="/gallery">
                                <BookOpenIcon className="mr-2 h-4 w-4"/>
                                公开论文库
                            </Link>
                        </Button>
                        <Button size="lg" variant="outline" className="h-12 px-8 text-base" asChild>
                            <Link to="/public/tasks">
                                <SparklesIcon className="mr-2 h-4 w-4"/>
                                公开翻译任务
                            </Link>
                        </Button>
                    </div>

                    <div
                        className="animate-fade-up-d3 mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
                        {["Arxiv", "LaTeX ZIP", "PDF"].map((t) => (
                            <span key={t} className="flex items-center gap-1.5">
                <CheckCircle2Icon className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0"/>
                                {t}
              </span>
                        ))}
                    </div>
                </div>

                {/* Scroll indicator */}
                <div
                    className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-muted-foreground/50">
                    <div className="h-10 w-[1px] bg-gradient-to-b from-transparent to-muted-foreground/30"/>
                </div>
            </section>

        </div>
    )
}
