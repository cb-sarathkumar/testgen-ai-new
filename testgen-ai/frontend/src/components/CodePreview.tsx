import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow, tomorrowNight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Button } from './UI/Button';
import { Card, CardContent, CardHeader, CardTitle } from './UI/Card';
import { Badge } from './UI/Badge';
import { Download, Copy, Check } from 'lucide-react';
import toast from 'react-hot-toast';

interface CodePreviewProps {
  files: Record<string, string>;
  title?: string;
  onDownload?: () => void;
}

export function CodePreview({ files, title = "Generated Code", onDownload }: CodePreviewProps) {
  const [selectedFile, setSelectedFile] = useState<string>(Object.keys(files)[0] || '');
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  const getLanguageFromFileName = (fileName: string): string => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'java':
        return 'java';
      case 'feature':
        return 'gherkin';
      case 'xml':
        return 'xml';
      case 'properties':
        return 'properties';
      case 'md':
        return 'markdown';
      case 'json':
        return 'json';
      case 'yml':
      case 'yaml':
        return 'yaml';
      default:
        return 'text';
    }
  };

  const copyToClipboard = async (content: string, fileName: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedFile(fileName);
      toast.success('Code copied to clipboard!');
      setTimeout(() => setCopiedFile(null), 2000);
    } catch (err) {
      toast.error('Failed to copy code');
    }
  };

  const downloadFile = (fileName: string, content: string) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success(`Downloaded ${fileName}`);
  };

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'java':
        return '☕';
      case 'feature':
        return '🥒';
      case 'xml':
        return '📄';
      case 'properties':
        return '⚙️';
      case 'md':
        return '📝';
      default:
        return '📄';
    }
  };

  if (!files || Object.keys(files).length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <p className="text-gray-500">No files to preview</p>
        </CardContent>
      </Card>
    );
  }

  const fileList = Object.keys(files);
  const currentContent = files[selectedFile] || '';

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{title}</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              {fileList.length} file{fileList.length !== 1 ? 's' : ''}
            </Badge>
            {onDownload && (
              <Button
                variant="outline"
                size="sm"
                onClick={onDownload}
              >
                <Download className="h-4 w-4 mr-2" />
                Download All
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <div className="flex h-96">
          {/* File List */}
          <div className="w-1/3 border-r border-gray-200 bg-gray-50">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-sm font-medium text-gray-700">Files</h3>
            </div>
            <div className="overflow-y-auto max-h-80">
              {fileList.map((fileName) => (
                <button
                  key={fileName}
                  onClick={() => setSelectedFile(fileName)}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors flex items-center gap-2 ${
                    selectedFile === fileName ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-500' : 'text-gray-700'
                  }`}
                >
                  <span>{getFileIcon(fileName)}</span>
                  <span className="truncate">{fileName}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Code Content */}
          <div className="flex-1 flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center gap-2">
                <span>{getFileIcon(selectedFile)}</span>
                <span className="text-sm font-medium text-gray-700">{selectedFile}</span>
                <Badge variant="outline" className="text-xs">
                  {getLanguageFromFileName(selectedFile)}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(currentContent, selectedFile)}
                >
                  {copiedFile === selectedFile ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => downloadFile(selectedFile, currentContent)}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            <div className="flex-1 overflow-auto">
              <SyntaxHighlighter
                language={getLanguageFromFileName(selectedFile)}
                style={tomorrow}
                customStyle={{
                  margin: 0,
                  height: '100%',
                  fontSize: '13px',
                  lineHeight: '1.5',
                }}
                showLineNumbers
                wrapLines
                wrapLongLines
              >
                {currentContent}
              </SyntaxHighlighter>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
