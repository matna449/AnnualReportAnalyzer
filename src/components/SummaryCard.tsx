import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

interface SummaryCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ title, value, icon }) => {
  return (
    <Card sx={{ minWidth: 200, height: '100%' }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Typography variant="h6" component="div" color="text.secondary">
            {title}
          </Typography>
          <Box sx={{ color: 'primary.main' }}>
            {icon}
          </Box>
        </Box>
        <Typography variant="h4" component="div">
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default SummaryCard; 