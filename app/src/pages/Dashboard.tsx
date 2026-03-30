import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Upload, 
  Camera, 
  FileText, 
  Sparkles, 
  Download,
  Volume2,
  LogOut,
  History,
  Smile,
  Meh,
  Frown
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

const Dashboard = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [showResults, setShowResults] = useState(false);

  // Mock results data
  const [results, setResults] = useState({
    extractedText: "",
    summary: "",
    sentiment: "neutral" as "positive" | "neutral" | "negative",
    keywords: [] as string[]
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      toast.success("File selected successfully!");
    }
  };

  const handleProcess = async () => {
    if (!selectedFile) {
      toast.error("Please select a file first");
      return;
    }

    setProcessing(true);
    
    // TODO: Implement actual processing with backend
    setTimeout(() => {
      setResults({
        extractedText: "Mahatma Gandhi led the Dandi March in 1930. This peaceful protest was a significant act of civil disobedience against the British salt tax in colonial India. The march covered 240 miles over 24 days, from Sabarmati Ashram to Dandi, Gujarat. It marked a turning point in India's independence movement.",
        summary: "Gandhi initiated a peaceful protest against the British salt tax in 1930. The Dandi March covered 240 miles over 24 days and became a pivotal moment in India's independence movement.",
        sentiment: "positive",
        keywords: ["Gandhi", "1930", "Dandi March", "independence", "British", "protest"]
      });
      setProcessing(false);
      setShowResults(true);
      toast.success("Document processed successfully!");
    }, 3000);
  };

  const getSentimentIcon = () => {
    switch (results.sentiment) {
      case "positive":
        return <Smile className="w-6 h-6 text-green-500" />;
      case "negative":
        return <Frown className="w-6 h-6 text-red-500" />;
      default:
        return <Meh className="w-6 h-6 text-yellow-500" />;
    }
  };

  const getSentimentColor = () => {
    switch (results.sentiment) {
      case "positive":
        return "bg-green-500";
      case "negative":
        return "bg-red-500";
      default:
        return "bg-yellow-500";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border backdrop-blur-md bg-background/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-primary" />
            <h1 className="text-2xl font-bold text-gradient">TEXTOR</h1>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => navigate("/ocr")}>OCR Playground</Button>
            <Button variant="ghost" size="icon">
              <History className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => navigate("/")}>
              <LogOut className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Welcome Section */}
        <div className="mb-8 animate-fade-in">
          <h2 className="text-3xl font-bold mb-2">Welcome back, User!</h2>
          <p className="text-muted-foreground text-lg">
            Upload a document to extract text, generate summaries, and analyze sentiment
          </p>
        </div>

        {/* Upload Section */}
        {!showResults && (
          <Card className="border-border card-shadow mb-8 animate-scale-in">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5 text-primary" />
                Upload Document
              </CardTitle>
              <CardDescription>
                Choose how you want to input your handwritten document
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="upload" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="upload">
                    <Upload className="w-4 h-4 mr-2" />
                    Upload
                  </TabsTrigger>
                  <TabsTrigger value="pdf">
                    <FileText className="w-4 h-4 mr-2" />
                    PDF
                  </TabsTrigger>
                  <TabsTrigger value="camera">
                    <Camera className="w-4 h-4 mr-2" />
                    Camera
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="upload" className="space-y-4">
                  <div className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary transition-colors">
                    <Input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="file-upload"
                    />
                    <Label htmlFor="file-upload" className="cursor-pointer">
                      <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                      <p className="text-lg font-medium mb-2">
                        {selectedFile ? selectedFile.name : "Click to upload or drag and drop"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        PNG, JPG up to 10MB
                      </p>
                    </Label>
                  </div>
                </TabsContent>

                <TabsContent value="pdf">
                  <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
                    <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-lg font-medium mb-2">PDF Upload Coming Soon</p>
                  </div>
                </TabsContent>

                <TabsContent value="camera">
                  <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
                    <Camera className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-lg font-medium mb-2">Camera Capture Coming Soon</p>
                  </div>
                </TabsContent>
              </Tabs>

              <Button
                variant="gradient"
                className="w-full mt-4"
                onClick={handleProcess}
                disabled={!selectedFile || processing}
              >
                {processing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-2" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Process Document
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Results Section */}
        {showResults && (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-bold">Processing Results</h3>
              <Button variant="outline" onClick={() => {
                setShowResults(false);
                setSelectedFile(null);
              }}>
                Process Another Document
              </Button>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Extracted Text */}
              <Card className="border-border card-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary" />
                    Extracted Text
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="bg-secondary/50 rounded-lg p-4 min-h-[200px]">
                    <p className="text-sm leading-relaxed">{results.extractedText}</p>
                  </div>
                  <Button variant="outline" className="w-full mt-4">
                    <Download className="w-4 h-4 mr-2" />
                    Download Text
                  </Button>
                </CardContent>
              </Card>

              {/* Summary */}
              <Card className="border-border card-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary" />
                    Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="bg-secondary/50 rounded-lg p-4 min-h-[200px]">
                    <p className="text-sm leading-relaxed">{results.summary}</p>
                    
                    <div className="mt-4 pt-4 border-t border-border">
                      <p className="text-xs font-medium text-muted-foreground mb-2">Keywords:</p>
                      <div className="flex flex-wrap gap-2">
                        {results.keywords.map((keyword, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-primary/20 text-primary rounded-full text-xs font-medium"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <Button variant="outline" className="flex-1">
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </Button>
                    <Button variant="outline" className="flex-1">
                      <Volume2 className="w-4 h-4 mr-2" />
                      Listen
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sentiment Analysis */}
            <Card className="border-border card-shadow">
              <CardHeader>
                <CardTitle>Sentiment Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3">
                    {getSentimentIcon()}
                    <span className="text-lg font-medium capitalize">{results.sentiment}</span>
                  </div>
                  <div className="flex-1 h-4 bg-secondary rounded-full overflow-hidden">
                    <div className={`h-full ${getSentimentColor()} transition-all`} style={{ width: '75%' }} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
