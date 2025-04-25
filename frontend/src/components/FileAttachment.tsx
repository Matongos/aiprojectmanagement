import React, { useState } from 'react';
import { 
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardFooter,
  Input,
  Label
} from '@/components/ui';
import { Paperclip, File, Download, Trash2, Upload } from 'lucide-react';
import { formatBytes } from '@/lib/utils';

export interface FileAttachmentProps {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  description?: string;
  task_id: number;
  uploaded_by: number;
  created_at: string;
  updated_at?: string;
}

interface FileAttachmentListProps {
  taskId: number;
  attachments: FileAttachmentProps[];
  onUpload: (file: File, description?: string) => Promise<void>;
  onDelete: (fileId: number) => Promise<void>;
  isLoading?: boolean;
}

export const FileAttachmentList: React.FC<FileAttachmentListProps> = ({
  taskId,
  attachments,
  onUpload,
  onDelete,
  isLoading = false
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    setIsUploading(true);
    try {
      await onUpload(selectedFile, description);
      setSelectedFile(null);
      setDescription('');
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Paperclip className="h-5 w-5" />
          Attachments
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* File upload form */}
          <div className="space-y-2">
            <Label htmlFor="file-upload">Upload new attachment</Label>
            <div className="flex items-start gap-2">
              <Input
                id="file-upload"
                type="file"
                onChange={handleFileChange}
                disabled={isUploading}
              />
              <Button 
                onClick={handleUpload} 
                disabled={!selectedFile || isUploading}
                variant="secondary"
                size="sm"
              >
                {isUploading ? 'Uploading...' : 'Upload'}
              </Button>
            </div>
            {selectedFile && (
              <div className="mt-2">
                <Label htmlFor="file-description">Description (optional)</Label>
                <Input
                  id="file-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter file description"
                  className="mt-1"
                />
              </div>
            )}
          </div>

          {/* Attachments list */}
          {attachments.length === 0 ? (
            <div className="text-center text-muted-foreground py-4">
              No attachments yet
            </div>
          ) : (
            <div className="space-y-2">
              {attachments.map((attachment) => (
                <FileAttachmentItem
                  key={attachment.id}
                  attachment={attachment}
                  onDelete={onDelete}
                  isLoading={isLoading}
                />
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

interface FileAttachmentItemProps {
  attachment: FileAttachmentProps;
  onDelete: (fileId: number) => Promise<void>;
  isLoading?: boolean;
}

export const FileAttachmentItem: React.FC<FileAttachmentItemProps> = ({
  attachment,
  onDelete,
  isLoading = false
}) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this file?')) {
      setIsDeleting(true);
      try {
        await onDelete(attachment.id);
      } catch (error) {
        console.error('Error deleting file:', error);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  const getDownloadUrl = () => {
    return `/api/file-attachments/${attachment.id}/download`;
  };

  return (
    <div className="flex items-center justify-between p-3 border rounded-md">
      <div className="flex items-center gap-3">
        <File className="h-5 w-5 text-blue-500" />
        <div>
          <p className="font-medium">{attachment.original_filename}</p>
          <p className="text-xs text-muted-foreground">
            {formatBytes(attachment.file_size)} • {new Date(attachment.created_at).toLocaleDateString()}
          </p>
          {attachment.description && (
            <p className="text-sm mt-1">{attachment.description}</p>
          )}
        </div>
      </div>
      <div className="flex gap-2">
        <a 
          href={getDownloadUrl()} 
          target="_blank" 
          rel="noopener noreferrer"
        >
          <Button variant="ghost" size="icon">
            <Download className="h-4 w-4" />
          </Button>
        </a>
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={handleDelete}
          disabled={isDeleting || isLoading}
        >
          <Trash2 className="h-4 w-4 text-red-500" />
        </Button>
      </div>
    </div>
  );
}; 