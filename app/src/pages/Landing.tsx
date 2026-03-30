import { Button } from "@/components/ui/button";
import { ArrowRight, Upload, Camera, FileText, Sparkles, Languages, TrendingUp } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-background/80 border-b border-border">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-primary" />
            <h1 className="text-2xl font-bold text-gradient">TEXTOR</h1>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate("/ocr")}>OCR Playground</Button>
            <Button variant="ghost" onClick={() => navigate("/auth")}>
              Login
            </Button>
            <Button variant="gradient" onClick={() => navigate("/auth")}>
              Get Started
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="container mx-auto max-w-6xl">
          <div className="text-center space-y-6 animate-fade-in">
            <div className="inline-block px-4 py-2 bg-primary/10 border border-primary/20 rounded-full mb-4">
              <span className="text-primary font-medium">AI-Powered Document Intelligence</span>
            </div>
            <h2 className="text-5xl md:text-7xl font-bold leading-tight">
              Transform Handwritten
              <br />
              <span className="text-gradient">Text into Digital Gold</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              TEXTOR is an AI-powered platform that digitizes handwritten documents into editable text,
              summarizes key insights, and highlights important dates, names, and keywords — supporting
              multiple languages and real-time camera capture.
            </p>
            <div className="flex items-center justify-center gap-4 pt-4">
              <Button variant="gradient" size="lg" onClick={() => navigate("/auth")} className="group">
                Start Free Trial
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Button>
              <Button variant="outline" size="lg">
                Watch Demo
              </Button>
            </div>
          </div>

          {/* Feature Cards */}
          <div className="grid md:grid-cols-3 gap-6 mt-20 animate-fade-in-up">
            <div className="gradient-card p-6 rounded-xl border border-border card-shadow hover:scale-105 transition-transform">
              <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center mb-4">
                <Upload className="w-6 h-6 text-primary-foreground" />
              </div>
              <h3 className="text-xl font-bold mb-2">Multiple Input Methods</h3>
              <p className="text-muted-foreground">
                Upload images, PDFs, or capture directly from your camera for instant processing
              </p>
            </div>

            <div className="gradient-card p-6 rounded-xl border border-border card-shadow hover:scale-105 transition-transform">
              <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center mb-4">
                <FileText className="w-6 h-6 text-primary-foreground" />
              </div>
              <h3 className="text-xl font-bold mb-2">Smart Extraction</h3>
              <p className="text-muted-foreground">
                Advanced AI extracts text, generates summaries, and performs sentiment analysis
              </p>
            </div>

            <div className="gradient-card p-6 rounded-xl border border-border card-shadow hover:scale-105 transition-transform">
              <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center mb-4">
                <Languages className="w-6 h-6 text-primary-foreground" />
              </div>
              <h3 className="text-xl font-bold mb-2">Multilingual Support</h3>
              <p className="text-muted-foreground">
                Auto-detect languages and translate extracted text into multiple languages
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-secondary/20">
        <div className="container mx-auto max-w-6xl">
          <div className="text-center mb-16">
            <h3 className="text-4xl font-bold mb-4">Powerful Features</h3>
            <p className="text-xl text-muted-foreground">Everything you need to digitize your documents</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="flex gap-4">
              <div className="w-12 h-12 gradient-accent rounded-lg flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-6 h-6 text-accent-foreground" />
              </div>
              <div>
                <h4 className="text-xl font-bold mb-2">AI-Powered OCR</h4>
                <p className="text-muted-foreground">
                  State-of-the-art Donut model for accurate handwritten text recognition
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="w-12 h-12 gradient-accent rounded-lg flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-6 h-6 text-accent-foreground" />
              </div>
              <div>
                <h4 className="text-xl font-bold mb-2">Sentiment Analysis</h4>
                <p className="text-muted-foreground">
                  Understand the emotional tone of your documents with visual indicators
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="w-12 h-12 gradient-accent rounded-lg flex items-center justify-center flex-shrink-0">
                <Camera className="w-6 h-6 text-accent-foreground" />
              </div>
              <div>
                <h4 className="text-xl font-bold mb-2">Real-Time Capture</h4>
                <p className="text-muted-foreground">
                  Use your device camera to instantly capture and process documents
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="w-12 h-12 gradient-accent rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-accent-foreground" />
              </div>
              <div>
                <h4 className="text-xl font-bold mb-2">Smart Summaries</h4>
                <p className="text-muted-foreground">
                  Auto-highlight keywords, dates, and important information in summaries
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto max-w-4xl">
          <div className="gradient-card p-12 rounded-2xl border border-border card-shadow text-center">
            <h3 className="text-4xl font-bold mb-4">Ready to Transform Your Documents?</h3>
            <p className="text-xl text-muted-foreground mb-8">
              Join thousands of users who are digitizing their handwritten documents with TEXTOR
            </p>
            <Button variant="accent" size="lg" onClick={() => navigate("/auth")} className="group">
              Start Your Free Trial
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-border">
        <div className="container mx-auto text-center text-muted-foreground">
          <p>&copy; 2025 TEXTOR. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
