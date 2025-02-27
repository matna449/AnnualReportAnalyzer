import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from 'recharts';

// Sample data - in a real app, this would come from an API
const sampleData = [
  { year: '2019', revenue: 4000, profit: 2400 },
  { year: '2020', revenue: 3000, profit: 1398 },
  { year: '2021', revenue: 5000, profit: 3000 },
  { year: '2022', revenue: 7800, profit: 3908 },
  { year: '2023', revenue: 9000, profit: 4800 },
];

interface FinancialPerformanceChartProps {
  title?: string;
  data?: Array<{
    year: string;
    revenue: number;
    profit: number;
  }>;
}

const FinancialPerformanceChart: React.FC<FinancialPerformanceChartProps> = ({ 
  title = "Financial Performance Trends",
  data = sampleData 
}) => {
  return (
    <Card sx={{ width: '100%', height: '100%', minHeight: 400 }}>
      <CardContent>
        <Typography variant="h6" component="div" gutterBottom>
          {title}
        </Typography>
        <Box sx={{ width: '100%', height: 350 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis />
              <Tooltip 
                formatter={(value) => [`$${value.toLocaleString()}`, undefined]}
                labelFormatter={(label) => `Year: ${label}`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="#8884d8"
                activeDot={{ r: 8 }}
                name="Revenue"
              />
              <Line 
                type="monotone" 
                dataKey="profit" 
                stroke="#82ca9d" 
                name="Profit"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default FinancialPerformanceChart; 