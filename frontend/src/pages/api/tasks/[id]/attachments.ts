import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query;
  
  if (!id || typeof id !== 'string') {
    return res.status(400).json({ error: 'Invalid task ID' });
  }
  
  // Get token from the request
  const token = req.headers.authorization?.split(' ')[1] || '';
  
  // Forward the request to the backend
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  try {
    const response = await fetch(`${backendUrl}/tasks/${id}/attachments`, {
      method: req.method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      return res.status(response.status).json(errorData);
    }
    
    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Error fetching task attachments:', error);
    return res.status(500).json({ error: 'Failed to fetch task attachments' });
  }
} 