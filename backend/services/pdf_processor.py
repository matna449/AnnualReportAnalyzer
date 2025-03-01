import os
import re
import logging
import PyPDF2
import pdfplumber
import tabula
import pandas as pd
from typing import List, Dict, Any, Tuple, Set, Optional
from sqlalchemy.orm import Session

from services.pdf_service import PDFService
from services.ai_service import AIService
from services.db_service import DBService
from models.schemas import MetricCreate, SummaryCreate

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Service for selectively processing financial sections from annual reports."""
    
    def __init__(self):
        self.pdf_service = PDFService()
        self.ai_service = AIService()
        self.db_service = DBService()
    
    def process_annual_report(self, file_path: str, report_id: int, db: Session) -> Dict[str, Any]:
        """
        Main method to process an annual report PDF.
        
        Args:
            file_path: Path to the PDF file
            report_id: ID of the report in the database
            db: Database session
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting selective processing of annual report: {file_path}")
            
            # First pass: Identify financial sections
            toc_pages, financial_pages = self.identify_financial_sections(file_path)
            
            if not financial_pages:
                logger.warning(f"No financial sections identified in {file_path}")
                return {"error": "No financial sections identified in the report"}
            
            logger.info(f"Identified {len(financial_pages)} financial pages")
            
            # Extract text and tables from financial sections only
            financial_data = self.extract_financial_sections(file_path, financial_pages)
            
            # Calculate financial KPIs
            kpis = self.calculate_financial_kpis(financial_data)
            
            # Generate AI summaries and insights
            insights = self.generate_ai_insights(financial_data, kpis)
            
            # Store results in database
            self.store_results(db, report_id, kpis, insights)
            
            return {
                "success": True,
                "financial_pages": financial_pages,
                "kpis": kpis,
                "insights": insights
            }
            
        except Exception as e:
            logger.error(f"Error processing annual report: {str(e)}")
            # Update report status to failed
            self.db_service.update_report_status(db, report_id, "failed")
            raise
    
    def identify_financial_sections(self, file_path: str) -> Tuple[List[int], Set[int]]:
        """
        First pass to identify pages containing financial information.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (table of contents pages, financial section pages)
        """
        financial_pages = set()
        toc_pages = []
        
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)
                
                # Financial section keywords to look for
                financial_keywords = [
                    "financial statements", "consolidated financial", 
                    "balance sheet", "income statement", "statement of income",
                    "cash flow statement", "statement of cash flows",
                    "statement of financial position", "notes to financial",
                    "financial results", "financial review", "financial performance"
                ]
                
                # Regex patterns for finding page references in TOC
                toc_pattern = re.compile(r'(table\s+of\s+contents|index)', re.IGNORECASE)
                page_ref_pattern = re.compile(
                    r'(' + '|'.join(financial_keywords) + r')\s*\.{0,3}\s*(\d+)', 
                    re.IGNORECASE
                )
                
                # First scan for TOC pages
                for i in range(min(20, total_pages)):  # Check first 20 pages for TOC
                    page_text = reader.pages[i].extract_text()
                    if toc_pattern.search(page_text):
                        toc_pages.append(i)
                        
                        # Extract page references from TOC
                        for match in page_ref_pattern.finditer(page_text):
                            try:
                                page_num = int(match.group(2))
                                # Adjust for 0-indexing if needed
                                if page_num <= total_pages:
                                    financial_pages.add(page_num - 1)  # Convert to 0-indexed
                            except ValueError:
                                continue
                
                # If no TOC found or few financial pages identified, scan all pages
                if len(financial_pages) < 5:
                    logger.info("Few financial pages found from TOC, scanning all pages")
                    
                    # Scan each page for financial keywords
                    for i in range(total_pages):
                        if i % 50 == 0:  # Log progress for large documents
                            logger.info(f"Scanning page {i}/{total_pages}")
                            
                        page_text = reader.pages[i].extract_text().lower()
                        
                        # Check for financial section headers
                        if any(keyword.lower() in page_text for keyword in financial_keywords):
                            financial_pages.add(i)
                            
                            # Also add the next few pages as they likely contain financial data
                            for j in range(1, 5):
                                if i + j < total_pages:
                                    financial_pages.add(i + j)
                
                # Add pages with tables that look like financial tables
                with pdfplumber.open(file_path) as pdf:
                    for i in range(total_pages):
                        if i % 50 == 0:
                            logger.info(f"Checking for tables on page {i}/{total_pages}")
                            
                        if i not in financial_pages:  # Skip pages we've already identified
                            try:
                                page = pdf.pages[i]
                                tables = page.extract_tables()
                                
                                if tables and len(tables) > 0:
                                    # Check if any table has financial data indicators
                                    for table in tables:
                                        if table and len(table) > 1:  # At least header + one row
                                            table_text = ' '.join([' '.join([str(cell) for cell in row if cell]) for row in table])
                                            if any(re.search(r'\b' + re.escape(kw) + r'\b', table_text, re.IGNORECASE) for kw in [
                                                'revenue', 'income', 'assets', 'liabilities', 'equity', 
                                                'cash', 'profit', 'loss', 'earnings', 'expense'
                                            ]):
                                                financial_pages.add(i)
                                                break
                            except Exception as e:
                                logger.warning(f"Error checking tables on page {i}: {str(e)}")
                                continue
                
                logger.info(f"Identified {len(toc_pages)} TOC pages and {len(financial_pages)} financial pages")
                return toc_pages, financial_pages
                
        except Exception as e:
            logger.error(f"Error identifying financial sections: {str(e)}")
            raise
    
    def extract_financial_sections(self, file_path: str, financial_pages: Set[int]) -> Dict[str, Any]:
        """
        Extract text and tables from identified financial pages.
        
        Args:
            file_path: Path to the PDF file
            financial_pages: Set of page numbers (0-indexed) containing financial information
            
        Returns:
            Dictionary with extracted financial data
        """
        result = {
            "text": "",
            "tables": [],
            "page_texts": {}
        }
        
        try:
            # Extract text from financial pages
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                for i in sorted(financial_pages):
                    try:
                        page_text = reader.pages[i].extract_text()
                        result["text"] += page_text + "\n\n"
                        result["page_texts"][i] = page_text
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {i}: {str(e)}")
            
            # Extract tables from financial pages using tabula-py
            try:
                # Convert 0-indexed to 1-indexed for tabula
                tabula_pages = [i + 1 for i in financial_pages]
                
                # Extract tables
                tables = tabula.read_pdf(
                    file_path,
                    pages=tabula_pages,
                    multiple_tables=True,
                    pandas_options={'header': None}
                )
                
                # Process tables
                for i, table in enumerate(tables):
                    if not table.empty:
                        # Clean table data
                        table = table.fillna('')
                        table_dict = {
                            "table_id": i,
                            "data": table.values.tolist()
                        }
                        result["tables"].append(table_dict)
                
                logger.info(f"Extracted {len(result['tables'])} tables from financial pages")
                
            except Exception as e:
                logger.error(f"Error extracting tables with tabula: {str(e)}")
                
                # Fallback to pdfplumber for table extraction
                logger.info("Falling back to pdfplumber for table extraction")
                with pdfplumber.open(file_path) as pdf:
                    table_id = 0
                    for i in sorted(financial_pages):
                        try:
                            page = pdf.pages[i]
                            tables = page.extract_tables()
                            
                            for table in tables:
                                if table and len(table) > 0:
                                    table_dict = {
                                        "table_id": table_id,
                                        "page": i,
                                        "data": table
                                    }
                                    result["tables"].append(table_dict)
                                    table_id += 1
                        except Exception as e:
                            logger.warning(f"Error extracting tables from page {i} with pdfplumber: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting financial sections: {str(e)}")
            raise
    
    def calculate_financial_kpis(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate financial KPIs from extracted data.
        
        Args:
            financial_data: Dictionary with extracted financial text and tables
            
        Returns:
            Dictionary with calculated KPIs
        """
        kpis = {}
        
        try:
            # Extract financial values using regex patterns
            text = financial_data["text"]
            
            # Helper function to find financial values
            def find_value(pattern, text, default=None):
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match and match.group(1):
                    # Clean the value and convert to float
                    value_str = match.group(1).replace(',', '').strip()
                    try:
                        return float(value_str)
                    except ValueError:
                        return default
                return default
            
            # Extract key financial figures
            revenue = find_value(r'(?:total\s+revenue|revenue)[^\n\d]+([\d,\.]+)', text)
            net_income = find_value(r'(?:net\s+income|net\s+profit|net\s+earnings)[^\n\d]+([\d,\.]+)', text)
            total_assets = find_value(r'(?:total\s+assets)[^\n\d]+([\d,\.]+)', text)
            total_liabilities = find_value(r'(?:total\s+liabilities)[^\n\d]+([\d,\.]+)', text)
            total_equity = find_value(r"(?:total\s+equity|shareholders['']?\s+equity)[^\n\d]+([\d,\.]+)", text)
            current_assets = find_value(r'(?:current\s+assets)[^\n\d]+([\d,\.]+)', text)
            current_liabilities = find_value(r'(?:current\s+liabilities)[^\n\d]+([\d,\.]+)', text)
            inventory = find_value(r'(?:inventory|inventories)[^\n\d]+([\d,\.]+)', text)
            cash = find_value(r'(?:cash\s+and\s+cash\s+equivalents|cash\s+equivalents)[^\n\d]+([\d,\.]+)', text)
            operating_income = find_value(r'(?:operating\s+income|income\s+from\s+operations)[^\n\d]+([\d,\.]+)', text)
            interest_expense = find_value(r'(?:interest\s+expense)[^\n\d]+([\d,\.]+)', text)
            
            # Store extracted values
            kpis["extracted_values"] = {
                "revenue": revenue,
                "net_income": net_income,
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
                "inventory": inventory,
                "cash": cash,
                "operating_income": operating_income,
                "interest_expense": interest_expense
            }
            
            # Calculate profitability metrics
            if net_income and total_equity:
                kpis["roe"] = (net_income / total_equity) * 100  # Return on Equity
            
            if net_income and total_assets:
                kpis["roa"] = (net_income / total_assets) * 100  # Return on Assets
            
            if net_income and revenue:
                kpis["net_profit_margin"] = (net_income / revenue) * 100  # Net Profit Margin
            
            # Calculate liquidity metrics
            if current_assets and current_liabilities:
                kpis["current_ratio"] = current_assets / current_liabilities  # Current Ratio
                
                if inventory and current_assets and current_liabilities:
                    kpis["quick_ratio"] = (current_assets - inventory) / current_liabilities  # Quick Ratio
                
                kpis["working_capital"] = current_assets - current_liabilities  # Working Capital
            
            # Calculate efficiency metrics
            if revenue and total_assets:
                kpis["asset_turnover"] = revenue / total_assets  # Asset Turnover
            
            if revenue and inventory:
                kpis["inventory_turnover"] = revenue / inventory  # Inventory Turnover (simplified)
            
            # Calculate solvency metrics
            if total_liabilities and total_equity:
                kpis["debt_to_equity"] = total_liabilities / total_equity  # Debt-to-Equity Ratio
            
            if operating_income and interest_expense and interest_expense > 0:
                kpis["interest_coverage"] = operating_income / interest_expense  # Interest Coverage Ratio
            
            # Calculate cash flow metrics
            if cash and current_liabilities:
                kpis["cash_ratio"] = cash / current_liabilities  # Cash Ratio
            
            # Remove None values
            kpis = {k: v for k, v in kpis.items() if v is not None}
            
            logger.info(f"Calculated {len(kpis)} financial KPIs")
            return kpis
            
        except Exception as e:
            logger.error(f"Error calculating financial KPIs: {str(e)}")
            # Return empty dict if calculation fails
            return kpis
    
    def generate_ai_insights(self, financial_data: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate AI-powered insights from financial data using Hugging Face.
        
        Args:
            financial_data: Dictionary with extracted financial text and tables
            kpis: Dictionary with calculated KPIs
            
        Returns:
            Dictionary with AI-generated insights
        """
        insights = {}
        
        try:
            # Prepare prompt with financial data and KPIs
            prompt = self._prepare_financial_prompt(financial_data, kpis)
            
            # Generate insights using Hugging Face API
            if hasattr(self.ai_service, 'huggingface_api_key') and self.ai_service.huggingface_api_key:
                # Use the AI service to generate insights
                model = "gpt2-finetuned-finance" if "gpt2-finetuned-finance" in self.ai_service.model_name else self.ai_service.model_name
                
                # Financial health summary
                financial_health_prompt = prompt + "\n\nProvide a concise summary of the company's financial health based on these metrics:"
                financial_health = self.ai_service.text_generation(financial_health_prompt, max_length=200)
                insights["financial_health"] = financial_health[0]["generated_text"] if isinstance(financial_health, list) else financial_health
                
                # Key trends
                trends_prompt = prompt + "\n\nIdentify the most important financial trends based on these metrics:"
                trends = self.ai_service.text_generation(trends_prompt, max_length=200)
                insights["key_trends"] = trends[0]["generated_text"] if isinstance(trends, list) else trends
                
                # Risk assessment
                risk_prompt = prompt + "\n\nAssess the key financial risks based on these metrics:"
                risks = self.ai_service.text_generation(risk_prompt, max_length=200)
                insights["risk_assessment"] = risks[0]["generated_text"] if isinstance(risks, list) else risks
                
                # Recommendations
                recommendations_prompt = prompt + "\n\nProvide recommendations for improvement based on these metrics:"
                recommendations = self.ai_service.text_generation(recommendations_prompt, max_length=200)
                insights["recommendations"] = recommendations[0]["generated_text"] if isinstance(recommendations, list) else recommendations
            else:
                # Fallback to basic insights if API key not available
                insights = self._generate_fallback_insights(kpis)
            
            logger.info("Generated AI insights for financial data")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
            # Return basic insights if AI generation fails
            return self._generate_fallback_insights(kpis)
    
    def _prepare_financial_prompt(self, financial_data: Dict[str, Any], kpis: Dict[str, Any]) -> str:
        """Prepare a prompt for the AI model with financial data and KPIs."""
        prompt = "Analyze the following financial metrics:\n\n"
        
        # Add KPIs to prompt
        for key, value in kpis.items():
            if key != "extracted_values" and isinstance(value, (int, float)):
                # Format the KPI name to be more readable
                formatted_key = key.replace('_', ' ').title()
                prompt += f"{formatted_key}: {value:.2f}\n"
        
        # Add extracted values
        if "extracted_values" in kpis:
            prompt += "\nExtracted Financial Values:\n"
            for key, value in kpis["extracted_values"].items():
                if value is not None:
                    formatted_key = key.replace('_', ' ').title()
                    prompt += f"{formatted_key}: {value:.2f}\n"
        
        return prompt
    
    def _generate_fallback_insights(self, kpis: Dict[str, Any]) -> Dict[str, str]:
        """Generate basic insights without AI when API is not available."""
        insights = {}
        
        # Financial health assessment
        if "current_ratio" in kpis:
            if kpis["current_ratio"] > 2:
                liquidity = "strong"
            elif kpis["current_ratio"] > 1:
                liquidity = "adequate"
            else:
                liquidity = "concerning"
                
            insights["financial_health"] = f"The company shows {liquidity} liquidity with a current ratio of {kpis.get('current_ratio', 0):.2f}."
        
        # Profitability assessment
        if "net_profit_margin" in kpis:
            if kpis["net_profit_margin"] > 20:
                profitability = "excellent"
            elif kpis["net_profit_margin"] > 10:
                profitability = "good"
            elif kpis["net_profit_margin"] > 5:
                profitability = "average"
            else:
                profitability = "below average"
                
            insights["key_trends"] = f"The company shows {profitability} profitability with a net profit margin of {kpis.get('net_profit_margin', 0):.2f}%."
        
        # Risk assessment
        if "debt_to_equity" in kpis:
            if kpis["debt_to_equity"] > 2:
                leverage = "highly leveraged, which may present financial risk"
            elif kpis["debt_to_equity"] > 1:
                leverage = "moderately leveraged"
            else:
                leverage = "conservatively financed"
                
            insights["risk_assessment"] = f"The company is {leverage} with a debt-to-equity ratio of {kpis.get('debt_to_equity', 0):.2f}."
        
        # Default insights if no KPIs available
        if not insights:
            insights = {
                "financial_health": "Insufficient data to assess financial health.",
                "key_trends": "Insufficient data to identify key trends.",
                "risk_assessment": "Insufficient data to assess financial risks.",
                "recommendations": "More financial data needed for meaningful recommendations."
            }
        elif "recommendations" not in insights:
            insights["recommendations"] = "Consider a more detailed analysis with complete financial statements."
        
        return insights
    
    def store_results(self, db: Session, report_id: int, kpis: Dict[str, Any], insights: Dict[str, str]) -> None:
        """
        Store calculated KPIs and insights in the database.
        
        Args:
            db: Database session
            report_id: ID of the report in the database
            kpis: Dictionary with calculated KPIs
            insights: Dictionary with AI-generated insights
        """
        try:
            # Store KPIs as metrics
            metrics_to_create = []
            
            # Add calculated KPIs
            for key, value in kpis.items():
                if key != "extracted_values" and isinstance(value, (int, float)):
                    metric = MetricCreate(
                        report_id=report_id,
                        name=key,
                        value=str(round(value, 4)),
                        category="financial"
                    )
                    metrics_to_create.append(metric)
            
            # Add extracted values
            if "extracted_values" in kpis:
                for key, value in kpis["extracted_values"].items():
                    if value is not None:
                        metric = MetricCreate(
                            report_id=report_id,
                            name=key,
                            value=str(round(value, 2)),
                            category="extracted"
                        )
                        metrics_to_create.append(metric)
            
            # Store metrics in batch
            if metrics_to_create:
                self.db_service.create_metrics_batch(db, metrics_to_create)
                logger.info(f"Stored {len(metrics_to_create)} metrics for report {report_id}")
            
            # Store insights as summaries
            summaries_to_create = []
            
            for key, value in insights.items():
                if value:
                    summary = SummaryCreate(
                        report_id=report_id,
                        category=key,
                        content=value
                    )
                    summaries_to_create.append(summary)
            
            # Store summaries in batch
            if summaries_to_create:
                self.db_service.create_summaries_batch(db, summaries_to_create)
                logger.info(f"Stored {len(summaries_to_create)} summaries for report {report_id}")
            
            # Update report status to completed
            self.db_service.update_report_status(db, report_id, "completed")
            
        except Exception as e:
            logger.error(f"Error storing results: {str(e)}")
            # Update report status to failed
            self.db_service.update_report_status(db, report_id, "failed")
            raise 