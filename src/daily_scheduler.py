"""
Daily scheduler service for automated market resolution monitoring.
"""
import asyncio
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import os
import time

from .market_monitor import MarketMonitor
from .resolution_researcher import GrokResolutionResearcher
from .blockchain.resolution import submit_market_answer
from .resolution_logger import resolution_logger
from .supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Email notification service for admin alerts"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.admin_email = os.getenv("ADMIN_EMAIL")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        
        if not all([self.smtp_username, self.smtp_password, self.admin_email]):
            logger.warning("Email configuration incomplete. Email notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
    
    def send_daily_report(self, summary: Dict, errors: List[Dict] = None):
        """
        Send daily operation report to admin
        
        Args:
            summary: Daily operation summary
            errors: List of errors encountered
        """
        if not self.enabled:
            logger.warning("Email notifications disabled due to missing configuration")
            return
        
        try:
            # Create email content
            subject = f"Supafund Market Resolution Daily Report - {summary['date']}"
            
            html_content = self._generate_report_html(summary, errors or [])
            text_content = self._generate_report_text(summary, errors or [])
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.admin_email
            
            # Add both plain text and HTML versions
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Daily report sent to {self.admin_email}")
            
        except Exception as e:
            logger.error(f"Failed to send daily report email: {e}")
    
    def send_error_alert(self, error_message: str, market_id: str = None, application_id: str = None):
        """
        Send immediate error alert to admin
        
        Args:
            error_message: Error description
            market_id: Related market ID if any
            application_id: Related application ID if any
        """
        if not self.enabled:
            return
        
        try:
            subject = "🚨 Supafund Market Resolution Error Alert"
            
            body = f"""
A critical error occurred in the market resolution system:

Error: {error_message}
Market ID: {market_id or 'N/A'}
Application ID: {application_id or 'N/A'}
Timestamp: {datetime.now(timezone.utc).isoformat()}

Please investigate this issue as soon as possible.

System: Supafund Market Creation Agent
"""
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.admin_email
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Error alert sent to {self.admin_email}")
            
        except Exception as e:
            logger.error(f"Failed to send error alert email: {e}")
    
    def _generate_report_html(self, summary: Dict, errors: List[Dict]) -> str:
        """Generate HTML version of the daily report"""
        
        error_section = ""
        if errors:
            error_rows = ""
            for error in errors[:10]:  # Limit to 10 most recent errors
                error_rows += f"""
                <tr>
                    <td>{error.get('market_id', 'N/A')}</td>
                    <td>{error.get('operation', 'N/A')}</td>
                    <td>{error.get('error_message', 'N/A')[:100]}...</td>
                </tr>
                """
            
            error_section = f"""
            <h3 style="color: #d32f2f;">Recent Errors ({len(errors)} total)</h3>
            <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
                <tr style="background-color: #f5f5f5;">
                    <th style="border: 1px solid #ddd; padding: 8px;">Market ID</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Operation</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Error Message</th>
                </tr>
                {error_rows}
            </table>
            """
        
        # Status indicator
        success_rate = summary.get('success_rate_percent', 0)
        status_color = "#4caf50" if success_rate >= 90 else "#ff9800" if success_rate >= 70 else "#d32f2f"
        status_text = "Excellent" if success_rate >= 90 else "Good" if success_rate >= 70 else "Needs Attention"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #1976d2; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .status {{ font-weight: bold; color: {status_color}; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Supafund Market Resolution Daily Report</h1>
                <p>Date: {summary['date']}</p>
            </div>
            
            <div class="summary">
                <h2>🎯 Summary</h2>
                <p><strong>System Status:</strong> <span class="status">{status_text}</span></p>
                <p><strong>Total Operations:</strong> {summary.get('total_operations', 0)}</p>
                <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
                <p><strong>Unique Markets Processed:</strong> {summary.get('unique_markets_processed', 0)}</p>
                <p><strong>Session Duration:</strong> {summary.get('session_duration_seconds', 0) / 3600:.1f} hours</p>
            </div>
            
            <h3>📈 Operation Breakdown</h3>
            <table>
                <tr>
                    <th>Operation</th>
                    <th>Started</th>
                    <th>Completed</th>
                    <th>Failed</th>
                    <th>Skipped</th>
                </tr>
        """
        
        for op_type, counts in summary.get('operation_counts', {}).items():
            html += f"""
                <tr>
                    <td>{op_type.replace('_', ' ').title()}</td>
                    <td>{counts.get('started', 0)}</td>
                    <td>{counts.get('completed', 0)}</td>
                    <td>{counts.get('failed', 0)}</td>
                    <td>{counts.get('skipped', 0)}</td>
                </tr>
            """
        
        html += f"""
            </table>
            
            {error_section}
            
            <div style="margin-top: 30px; padding: 15px; background-color: #e3f2fd; border-radius: 5px;">
                <p><strong>Generated by:</strong> Supafund Market Creation Agent</p>
                <p><strong>Report Time:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_report_text(self, summary: Dict, errors: List[Dict]) -> str:
        """Generate plain text version of the daily report"""
        
        error_section = ""
        if errors:
            error_section = f"\n\n🚨 RECENT ERRORS ({len(errors)} total):\n"
            error_section += "=" * 50 + "\n"
            for i, error in enumerate(errors[:5], 1):
                error_section += f"{i}. Market: {error.get('market_id', 'N/A')}\n"
                error_section += f"   Operation: {error.get('operation', 'N/A')}\n"
                error_section += f"   Error: {error.get('error_message', 'N/A')[:150]}...\n\n"
        
        success_rate = summary.get('success_rate_percent', 0)
        status_text = "EXCELLENT" if success_rate >= 90 else "GOOD" if success_rate >= 70 else "NEEDS ATTENTION"
        
        text = f"""
📊 SUPAFUND MARKET RESOLUTION DAILY REPORT
Date: {summary['date']}
{'=' * 60}

🎯 SUMMARY:
System Status: {status_text}
Total Operations: {summary.get('total_operations', 0)}
Success Rate: {success_rate:.1f}%
Unique Markets Processed: {summary.get('unique_markets_processed', 0)}
Session Duration: {summary.get('session_duration_seconds', 0) / 3600:.1f} hours

📈 OPERATION BREAKDOWN:
"""
        
        for op_type, counts in summary.get('operation_counts', {}).items():
            text += f"\n{op_type.replace('_', ' ').title()}:\n"
            text += f"  Started: {counts.get('started', 0)}\n"
            text += f"  Completed: {counts.get('completed', 0)}\n"
            text += f"  Failed: {counts.get('failed', 0)}\n"
            text += f"  Skipped: {counts.get('skipped', 0)}\n"
        
        text += error_section
        
        text += f"""

Generated by: Supafund Market Creation Agent
Report Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
        
        return text

class DailyResolutionScheduler:
    """Main scheduler service for daily market resolution operations"""
    
    def __init__(self):
        self.market_monitor = MarketMonitor()
        self.resolution_researcher = GrokResolutionResearcher()
        self.email_notifier = EmailNotifier()
        self.supabase = get_supabase_client()
        
        # Configuration
        self.min_research_confidence = float(os.getenv("MIN_RESEARCH_CONFIDENCE", "0.7"))
        self.max_markets_per_run = int(os.getenv("MAX_MARKETS_PER_RUN", "10"))
        self.resolution_delay_seconds = int(os.getenv("RESOLUTION_DELAY_SECONDS", "30"))
    
    async def run_daily_resolution_cycle(self) -> Dict:
        """
        Run the complete daily resolution cycle
        
        Returns:
            Summary dictionary of operations performed
        """
        logger.info("Starting daily market resolution cycle")
        cycle_start_time = time.time()
        
        try:
            # Step 1: Monitor markets for completion
            completed_markets = await self._monitor_markets()
            
            # Step 2: Research and resolve completed markets
            if completed_markets:
                await self._process_completed_markets(completed_markets)
            
            # Step 3: Check for markets needing finalization (using new system)
            await self._finalize_pending_resolutions()
            
            # Step 4: Generate and send daily summary
            cycle_duration = time.time() - cycle_start_time
            summary = resolution_logger.generate_daily_summary()
            summary['cycle_duration_seconds'] = cycle_duration
            
            # Send daily report
            errors = resolution_logger.get_recent_errors()
            self.email_notifier.send_daily_report(summary, errors)
            
            logger.info(f"Daily resolution cycle completed in {cycle_duration:.2f} seconds")
            return summary
            
        except Exception as e:
            error_msg = f"Critical error in daily resolution cycle: {e}"
            logger.error(error_msg)
            
            # Send immediate error alert
            self.email_notifier.send_error_alert(error_msg)
            
            # Still try to generate summary with error info
            summary = resolution_logger.generate_daily_summary()
            summary['critical_error'] = error_msg
            return summary
    
    async def _monitor_markets(self) -> List:
        """Monitor markets for completion"""
        op_id = resolution_logger.log_operation_start(
            "monitor", 
            "all_markets", 
            "system", 
            {"max_markets": self.max_markets_per_run}
        )
        
        start_time = time.time()
        
        try:
            completed_markets = self.market_monitor.check_completed_markets()
            
            # Limit the number of markets to process
            if len(completed_markets) > self.max_markets_per_run:
                logger.warning(f"Found {len(completed_markets)} completed markets, limiting to {self.max_markets_per_run}")
                completed_markets = completed_markets[:self.max_markets_per_run]
            
            duration = time.time() - start_time
            
            resolution_logger.log_operation_complete(
                op_id, 
                {
                    "completed_markets_found": len(completed_markets),
                    "market_ids": [m.market_id for m in completed_markets]
                },
                duration
            )
            
            resolution_logger.log_market_monitor_summary(
                total_markets=len(self.market_monitor.get_markets_to_monitor()),
                completed_markets=len(completed_markets)
            )
            
            return completed_markets
            
        except Exception as e:
            duration = time.time() - start_time
            resolution_logger.log_operation_failed(op_id, str(e), duration=duration)
            return []
    
    async def _process_completed_markets(self, completed_markets: List):
        """Process completed markets through research and resolution"""
        
        for i, market_status in enumerate(completed_markets, 1):
            logger.info(f"Processing market {i}/{len(completed_markets)}: {market_status.market_id}")
            
            try:
                # Research the resolution
                await self._research_market_resolution(market_status)
                
                # Add delay between markets to avoid rate limiting
                if i < len(completed_markets):
                    await asyncio.sleep(self.resolution_delay_seconds)
                    
            except Exception as e:
                error_msg = f"Error processing market {market_status.market_id}: {e}"
                logger.error(error_msg)
                self.email_notifier.send_error_alert(
                    error_msg, 
                    market_status.market_id, 
                    market_status.application_id
                )
    
    async def _research_market_resolution(self, market_status):
        """Research and submit resolution for a single market"""
        
        # Research resolution
        research_op_id = resolution_logger.log_operation_start(
            "research",
            market_status.market_id,
            market_status.application_id,
            {"funding_program": market_status.funding_program_name}
        )
        
        research_start_time = time.time()
        
        try:
            resolution_result = self.resolution_researcher.research_market_resolution(market_status)
            research_duration = time.time() - research_start_time
            
            if not resolution_result:
                resolution_logger.log_operation_failed(
                    research_op_id, 
                    "Failed to get resolution result from Grok API",
                    duration=research_duration
                )
                return
            
            resolution_logger.log_operation_complete(
                research_op_id,
                {
                    "outcome": resolution_result.outcome,
                    "confidence": resolution_result.confidence,
                    "sources_count": len(resolution_result.sources)
                },
                research_duration
            )
            
            # Log detailed research result
            resolution_logger.log_resolution_research_result(
                market_status.market_id,
                market_status.application_id,
                resolution_result.outcome,
                resolution_result.confidence,
                resolution_result.reasoning,
                resolution_result.sources
            )
            
            # Validate resolution confidence
            if not self.resolution_researcher.validate_resolution_result(
                resolution_result, 
                self.min_research_confidence
            ):
                logger.warning(f"Resolution result for {market_status.market_id} did not meet confidence threshold")
                return
            
            # Submit resolution to blockchain
            await self._submit_blockchain_resolution(market_status, resolution_result)
            
        except Exception as e:
            research_duration = time.time() - research_start_time
            resolution_logger.log_operation_failed(
                research_op_id, 
                str(e),
                duration=research_duration
            )
    
    async def _submit_blockchain_resolution(self, market_status, resolution_result):
        """Submit resolution to blockchain"""
        
        resolve_op_id = resolution_logger.log_operation_start(
            "resolve",
            market_status.market_id,
            market_status.application_id,
            {"outcome": resolution_result.outcome}
        )
        
        resolve_start_time = time.time()
        
        try:
            # Import config to get private key
            from .config import Config
            
            # Use new blockchain resolution system
            submission_result = submit_market_answer(
                market_id=market_status.market_id,
                outcome=resolution_result.outcome,
                confidence=resolution_result.confidence,
                reasoning=resolution_result.reasoning,
                from_private_key=Config.OMEN_PRIVATE_KEY,
                bond_amount_xdai=0.01,  # Default bond amount
                safe_address=None
            )
            
            resolve_duration = time.time() - resolve_start_time
            success = submission_result.success
            message = submission_result.raw_output or submission_result.error_message
            
            if success:
                resolution_logger.log_operation_complete(
                    resolve_op_id,
                    {"transaction_message": message},
                    resolve_duration
                )
                
                # Update market status in database
                self.market_monitor.update_market_status_in_db(
                    market_status.market_id,
                    "resolution_submitted",
                    {
                        "resolution_outcome": resolution_result.outcome,
                        "resolution_confidence": resolution_result.confidence,
                        "resolution_reasoning": resolution_result.reasoning,
                        "resolution_sources": resolution_result.sources,
                        "submitted_at": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                resolution_logger.log_operation_failed(
                    resolve_op_id,
                    message,
                    duration=resolve_duration
                )
                
                # Send immediate error alert for blockchain failures
                self.email_notifier.send_error_alert(
                    f"Blockchain resolution failed: {message}",
                    market_status.market_id,
                    market_status.application_id
                )
            
            # Log blockchain resolution result
            resolution_logger.log_blockchain_resolution(
                market_status.market_id,
                market_status.application_id,
                resolution_result.outcome,
                success,
                {"message": message}
            )
            
        except Exception as e:
            resolve_duration = time.time() - resolve_start_time
            resolution_logger.log_operation_failed(
                resolve_op_id,
                str(e),
                duration=resolve_duration
            )
    
    async def _finalize_pending_resolutions(self):
        """Check for and finalize markets that need final resolution"""
        
        try:
            # Get markets that have been resolved but may need finalization
            markets_to_check = self.supabase.table("prediction_markets").select(
                "*"
            ).eq("status", "resolution_submitted").execute()
            
            if not markets_to_check.data:
                return
            
            logger.info(f"Checking {len(markets_to_check.data)} markets for finalization")
            
            for market_record in markets_to_check.data:
                market_id = market_record.get("market_id", "")
                application_id = market_record.get("application_id", "")
                
                if not market_id:
                    continue
                
                finalize_op_id = resolution_logger.log_operation_start(
                    "finalize",
                    market_id,
                    application_id
                )
                
                try:
                    # Use new blockchain resolution system for finalization
                    from .blockchain.resolution import resolve_market_final, check_market_resolution_status
                    from .config import Config
                    
                    # Check if market needs finalization
                    success, check_message, status_info = check_market_resolution_status(
                        market_id=market_id,
                        from_private_key=Config.OMEN_PRIVATE_KEY
                    )
                    
                    if success and status_info.get("needs_finalization", False):
                        # Finalize the market using new system
                        finalize_result = resolve_market_final(
                            market_id=market_id,
                            from_private_key=Config.OMEN_PRIVATE_KEY,
                            safe_address=None
                        )
                        
                        if finalize_result.success:
                            resolution_logger.log_operation_complete(finalize_op_id, {"message": finalize_result.raw_output})
                            
                            # Update market status
                            self.market_monitor.update_market_status_in_db(
                                market_id,
                                "resolved",
                                {"finalized_at": datetime.now(timezone.utc).isoformat()}
                            )
                        else:
                            resolution_logger.log_operation_failed(finalize_op_id, finalize_result.error_message)
                    else:
                        resolution_logger.log_operation_skipped(finalize_op_id, check_message)
                        
                except Exception as e:
                    resolution_logger.log_operation_failed(finalize_op_id, str(e))
                
        except Exception as e:
            logger.error(f"Error in finalization check: {e}")

# Function to run the daily cycle (can be called by external schedulers)
async def run_daily_resolution():
    """Entry point for running the daily resolution cycle"""
    scheduler = DailyResolutionScheduler()
    return await scheduler.run_daily_resolution_cycle()

# For running from command line
if __name__ == "__main__":
    asyncio.run(run_daily_resolution())