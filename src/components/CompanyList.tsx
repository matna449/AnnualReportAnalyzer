'use client';

import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  Button,
  Chip
} from '@mui/material';
import { Visibility } from '@mui/icons-material';
import Link from 'next/link';

// Sample data - in a real app, this would come from an API
const sampleCompanies = [
  { 
    id: 1, 
    name: 'Apple Inc.', 
    ticker: 'AAPL', 
    sector: 'Technology', 
    latestReport: '2023',
    status: 'Completed'
  },
  { 
    id: 2, 
    name: 'Microsoft Corporation', 
    ticker: 'MSFT', 
    sector: 'Technology', 
    latestReport: '2023',
    status: 'Completed'
  },
  { 
    id: 3, 
    name: 'Tesla, Inc.', 
    ticker: 'TSLA', 
    sector: 'Automotive', 
    latestReport: '2022',
    status: 'Processing'
  },
  { 
    id: 4, 
    name: 'Amazon.com, Inc.', 
    ticker: 'AMZN', 
    sector: 'E-commerce', 
    latestReport: '2023',
    status: 'Completed'
  },
  { 
    id: 5, 
    name: 'Alphabet Inc.', 
    ticker: 'GOOGL', 
    sector: 'Technology', 
    latestReport: '2023',
    status: 'Completed'
  },
];

interface CompanyListProps {
  title?: string;
  companies?: Array<{
    id: number;
    name: string;
    ticker: string;
    sector: string;
    latestReport: string;
    status: 'Completed' | 'Processing' | 'Failed';
  }>;
}

const CompanyList: React.FC<CompanyListProps> = ({ 
  title = "Analyzed Companies",
  companies = sampleCompanies 
}) => {
  return (
    <Card sx={{ width: '100%', height: '100%' }}>
      <CardContent>
        <Typography variant="h6" component="div" gutterBottom>
          {title}
        </Typography>
        <TableContainer component={Paper} sx={{ maxHeight: 440 }}>
          <Table stickyHeader aria-label="company list table">
            <TableHead>
              <TableRow>
                <TableCell>Company</TableCell>
                <TableCell>Ticker</TableCell>
                <TableCell>Sector</TableCell>
                <TableCell>Latest Report</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {companies.map((company) => (
                <TableRow key={company.id}>
                  <TableCell component="th" scope="row">
                    {company.name}
                  </TableCell>
                  <TableCell>{company.ticker}</TableCell>
                  <TableCell>{company.sector}</TableCell>
                  <TableCell>{company.latestReport}</TableCell>
                  <TableCell>
                    <Chip 
                      label={company.status} 
                      color={
                        company.status === 'Completed' 
                          ? 'success' 
                          : company.status === 'Processing' 
                            ? 'warning' 
                            : 'error'
                      }
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Button 
                      size="small" 
                      variant="outlined" 
                      startIcon={<Visibility />}
                      href={`/reports/${company.id}`}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};

export default CompanyList; 