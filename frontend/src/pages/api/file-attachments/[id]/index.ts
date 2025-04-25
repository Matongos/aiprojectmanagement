import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query;
  
  if (!id || typeof id !== 'string') {
    return res.status(400).json({ error: 'Invalid file ID' });
  }
  
  if (req.method === 'DELETE') {
    // Get token from the request
    const token = req.headers.authorization?.split(' ')[1] || '';
    
    // Forward the request to the backend
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${backendUrl}/file-attachments/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          return res.status(404).json({ error: 'File not found' });
        }
        const errorData = await response.json();
        return res.status(response.status).json(errorData);
      }
      
      return res.status(204).end();
    } catch (error) {
      console.error('Error deleting file:', error);
      return res.status(500).json({ error: 'Failed to delete file' });
    }
  } else {
    res.setHeader('Allow', ['DELETE']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
} 