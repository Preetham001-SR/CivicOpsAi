'use client';

import { useState } from 'react';
import axios from 'axios';

interface FormData {
  text_description: string;
  latitude: number;
  longitude: number;
  address: string;
  photo: File | null;
  audio: File | null;
}

interface ComplaintResponse {
  id: string;
  status: string;
  created_at: string;
}

export default function UploadForm() {
  const [formData, setFormData] = useState<FormData>({
    text_description: '',
    latitude: 0,
    longitude: 0,
    address: '',
    photo: null,
    audio: null,
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ComplaintResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const data = new FormData();
      data.append('text_description', formData.text_description);
      data.append('latitude', formData.latitude.toString());
      data.append('longitude', formData.longitude.toString());
      data.append('address', formData.address);
      if (formData.photo) data.append('photo', formData.photo);
      if (formData.audio) data.append('audio', formData.audio);

      const response = await axios.post<ComplaintResponse>(
        '/api/v1/complaints',
        data,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      );

      setResult(response.data);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || 'Failed to submit complaint');
    } finally {
      setSubmitting(false);
    }
  };

  const getLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setFormData((prev) => ({
            ...prev,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          }));
        },
        () => alert('Unable to retrieve location')
      );
    } else {
      alert('Geolocation not supported');
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white py-8 px-6 shadow sm:rounded-lg sm:px-10">
          <h1 className="text-center text-3xl font-bold text-gray-900 mb-2">CivicOps AI</h1>
          <p className="text-center text-gray-600 mb-8">Report Infrastructure Issues</p>

          <form onSubmit={handleSubmit} className="space-y-6" encType="multipart/form-data">
            <div>
              <label htmlFor="text_description" className="block text-sm font-medium text-gray-700 mb-1">
                Description *
              </label>
              <textarea
                id="text_description"
                name="text_description"
                required
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Describe the issue (e.g., large pothole, broken streetlight)..."
                value={formData.text_description}
                onChange={(e) => setFormData({ ...formData, text_description: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="latitude" className="block text-sm font-medium text-gray-700 mb-1">
                  Latitude *
                </label>
                <input
                  type="number"
                  step="any"
                  id="latitude"
                  name="latitude"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  value={formData.latitude}
                  onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) })}
                />
              </div>
              <div>
                <label htmlFor="longitude" className="block text-sm font-medium text-gray-700 mb-1">
                  Longitude *
                </label>
                <input
                  type="number"
                  step="any"
                  id="longitude"
                  name="longitude"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  value={formData.longitude}
                  onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) })}
                />
              </div>
            </div>

            <div>
              <label htmlFor="address" className="block text-sm font-medium text-gray-700 mb-1">
                Address
              </label>
              <input
                type="text"
                id="address"
                name="address"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Main St & Oak Ave, New York, NY"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              />
            </div>

            <button
              type="button"
              onClick={getLocation}
              className="w-full inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Use Current Location
            </button>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Photo (optional)
              </label>
              <input
                type="file"
                accept="image/*"
                className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                onChange={(e) => setFormData({ ...formData, photo: e.target.files?.[0] || null })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Voice Recording (optional)
              </label>
              <input
                type="file"
                accept="audio/*"
                className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-medium file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
                onChange={(e) => setFormData({ ...formData, audio: e.target.files?.[0] || null })}
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
                {error}
              </div>
            )}

            {result && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
                <p className="font-medium">Complaint Submitted!</p>
                <p className="text-sm">ID: {result.id}</p>
                <p className="text-sm">Status: {result.status}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit Complaint'}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}