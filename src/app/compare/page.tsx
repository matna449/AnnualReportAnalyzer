'use client';

import React from 'react';
import { 
  Typography, 
  Paper
} from '@mui/material';
import PageLayout from '@/components/PageLayout';

export default function ComparePage() {
  return (
    <PageLayout>
      <Typography variant="h4" component="h1" gutterBottom>
        Compare Reports
      </Typography>
      
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6">
          Compare functionality coming soon!
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
          This page will allow you to compare financial metrics and business outlooks across different companies and time periods.
        </Typography>
      </Paper>
    </PageLayout>
  );
} 