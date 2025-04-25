import type { NextApiRequest, NextApiResponse } from 'next';
import formidable from 'formidable';
import { createReadStream } from 'fs';
import fetch from 'node-fetch';
import FormData from 'form-data';

// Disable the default body parser so we can parse the form data manually
export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'POST') {
    const form = new formidable.IncomingForm();
    
    try {
      const { fields, files } = await new Promise<{ fields: formidable.Fields; files: formidable.Files }>((resolve, reject) => {
        form.parse(req, (err, fields, files) => {
          if (err) return reject(err);
          resolve({ fields, files });
        });
      });
      
      // Get the file and form fields
      const file = files.file as formidable.File;
      const taskId = fields.task_id as string;
      const description = fields.description as string | undefined;
      
      if (!file || !taskId) {
        return res.status(400).json({ error: 'Missing required fields' });
      }
      
      // Get token from the request
      const token = req.headers.authorization?.split(' ')[1] || '';
      
      // Prepare form data for the backend
      const formData = new FormData();
      formData.append('file', createReadStream(file.filepath), {
        filename: file.originalFilename || 'file',
        contentType: file.mimetype || 'application/octet-stream',
      });
      formData.append('task_id', taskId);
      
      if (description) {
        formData.append('description', description);
      }
      
      // Forward the request to the backend
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/file-attachments/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          ...formData.getHeaders(),
        },
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        return res.status(response.status).json(errorData);
      }
      
      const data = await response.json();
      return res.status(201).json(data);
    } catch (error) {
      console.error('Error uploading file:', error);
      return res.status(500).json({ error: 'Failed to upload file' });
    }
  } else {
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
} 