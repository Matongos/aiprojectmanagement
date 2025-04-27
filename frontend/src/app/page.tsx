'use client';

import Link from 'next/link';
import Image from 'next/image';

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* Header/Navigation */}


      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto max-w-5xl">
          <div className="text-center mb-20">
            <div className="flex justify-center mb-6">
              <Image 
                src="/logo.png" 
                alt="ZINGSA Logo" 
                width={120} 
                height={120} 
                className="w-auto h-auto"
                priority
              />
            </div>
            <h1 className="text-5xl md:text-6xl font-bold mb-6 text-black">Exploring Space, Managing Excellence</h1>
            <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto">
              ZINGSA Project Management System streamlines space program workflows, enhancing collaboration and efficiency across Zimbabwe&apos;s geospatial initiatives.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-10 mb-20">
            <div className="bg-gray-50 p-8 rounded-lg text-center shadow-sm border border-gray-200">
              <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center text-black">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold mb-2 text-black">Mission Tracking</h2>
              <p className="text-gray-600">Monitor mission progress with real-time updates and comprehensive analytics.</p>
            </div>
            
            <div className="bg-gray-50 p-8 rounded-lg text-center shadow-sm border border-gray-200">
              <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center text-black">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold mb-2 text-black">Team Collaboration</h2>
              <p className="text-gray-600">Connect teams across departments with seamless communication tools.</p>
            </div>
            
            <div className="bg-gray-50 p-8 rounded-lg text-center shadow-sm border border-gray-200">
              <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center text-black">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
                </svg>
              </div>
              <h2 className="text-xl font-bold mb-2 text-black">Resource Allocation</h2>
              <p className="text-gray-600">Optimize resource distribution with AI-powered planning tools.</p>
            </div>
          </div>

          <div className="bg-gradient-to-r from-gray-100 to-white p-10 rounded-xl border border-gray-200 shadow-sm">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold mb-4 text-black">Advancing Zimbabwe&apos;s Space Exploration</h2>
              <p className="text-gray-600">
                ZINGSA integrates cutting-edge project management with space science expertise to drive technological innovation and national development.
              </p>
            </div>
            <div className="flex justify-center">
              <Link 
                href="/auth/login"
                className="bg-black text-white px-8 py-3 rounded-md font-medium hover:bg-gray-800 transition-colors"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-10 px-6 bg-gray-50">
        <div className="container mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-6 md:mb-0">
              <p className="text-gray-600">&copy; 2025 Zimbabwe National Geospatial and Space Agency. All rights reserved.</p>
            </div>
            <div className="flex space-x-6">
              <a href="#" className="text-gray-600 hover:text-black">Terms</a>
              <a href="#" className="text-gray-600 hover:text-black">Privacy</a>
              <a href="#" className="text-gray-600 hover:text-black">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
