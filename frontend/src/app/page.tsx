import { currentUser } from "@clerk/nextjs/server";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Pricing } from "@/components/landing/Pricing";
import { Navbar } from "@/components/landing/Navbar";
import { Footer } from "@/components/landing/Footer";

export default async function Home() {
  const user = await currentUser();

  return (
    <div className="flex min-h-screen flex-col bg-background font-body antialiased">
      <Navbar />
      <main className="flex-1">
        <Hero />

        <Features />
        <HowItWorks />
        <Pricing />

        {/* Blog Preview Placeholder */}
        <section id="blog" className="py-24 bg-background">
          <div className="container mx-auto px-6">
            <div className="mb-16">
              <h2 className="text-sm font-bold text-primary uppercase tracking-[0.3em] mb-4">Latest Insights</h2>
              <h3 className="text-4xl md:text-5xl font-black">Resources & News</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[1, 2, 3].map((i) => (
                <div key={i} className="group cursor-pointer">
                  <div className="aspect-video bg-muted rounded-3xl mb-6 overflow-hidden relative">
                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
                    {/* Placeholder for blog image */}
                    <div className="w-full h-full bg-primary/5 flex items-center justify-center text-primary/20 font-black text-4xl italic uppercase">Blog {i}</div>
                  </div>
                  <span className="inline-block px-3 py-1 rounded-full bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest mb-4">Article</span>
                  <h4 className="text-xl font-bold mb-4 group-hover:text-primary transition-colors">The Future of AI in Question Paper Design for 2026.</h4>
                  <p className="text-muted-foreground text-sm line-clamp-2">Exploring how generative models are transforming the way educators approach curriculum alignment.</p>
                </div>
              ))}
            </div>
          </div>
        </section>

      </main>
      <Footer />
    </div>
  );
}
