"""
Change Agent - Analyze code changes and generate impact summaries
"""
import json
import logging
from typing import Dict, List, Optional

from config import get_settings, PromptTemplates
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)
settings = get_settings()


class ChangeAgent:
    """
    Change Agent - Analyze code changes in PRs
    
    Responsibilities:
    - Monitor commits/PRs
    - Generate change summaries
    - Flag breaking changes
    - Identify affected documentation
    - Create risk assessments
    """
    
    def __init__(self):
        self.groq = get_groq_client()
        self.model = settings.groq_model_change
    
    def analyze_pr(self, pr_number: int, repo_url: str, diff: Optional[str] = None) -> Dict:
        """
        Analyze a pull request
        
        Args:
            pr_number: PR number
            repo_url: Repository URL
            diff: Optional git diff (will fetch if not provided)
            
        Returns:
            Dict with PR analysis
        """
        logger.info(f"Analyzing PR #{pr_number} in {repo_url}")
        
        # For demo, use sample diff if not provided
        if diff is None:
            diff = self._get_sample_diff()
        
        # Get historical context (from vector DB)
        context = "Historical context placeholder"
        
        # Generate analysis using Groq
        prompt = PromptTemplates.CHANGE_ANALYSIS.format(
            diff=diff[:2000],  # Limit diff size
            context=context
        )
        
        try:
            response = self.groq.complete(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.2,
                max_tokens=1024,
                json_mode=True
            )
            
            analysis = json.loads(response.content)
            analysis["pr_number"] = pr_number
            analysis["repo_url"] = repo_url
            
            logger.info(
                f"PR analysis complete: "
                f"{len(analysis.get('modified_files', []))} files modified, "
                f"{len(analysis.get('risk_flags', []))} risk flags"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing PR: {str(e)}")
            return {
                "pr_number": pr_number,
                "repo_url": repo_url,
                "summary": f"Error analyzing PR: {str(e)}",
                "error": str(e)
            }
    
    def _get_sample_diff(self) -> str:
        """Get sample diff for testing"""
        return """
diff --git a/src/api/payments.py b/src/api/payments.py
index abc123..def456 100644
--- a/src/api/payments.py
+++ b/src/api/payments.py
@@ -45,7 +45,7 @@ class PaymentProcessor:
-    def process_payment(self, amount: float, user_id: str) -> PaymentResult:
+    def process_payment(self, amount: Decimal, user_id: str, idempotency_key: str) -> PaymentResult:
         \"\"\"
-        Process a payment with retry logic
+        Process a payment with retry logic and idempotency support
         
         Args:
             amount: Payment amount
             user_id: User identifier
+            idempotency_key: Unique key to prevent duplicate charges
"""
    
    def generate_change_summary(self, diff: str) -> str:
        """
        Generate a human-readable change summary
        
        Args:
            diff: Git diff
            
        Returns:
            Change summary text
        """
        analysis = self.analyze_pr(0, "unknown", diff)
        
        summary_parts = [
            f"**Summary:** {analysis.get('summary', 'No summary available')}",
            ""
        ]
        
        # Modified files
        modified = analysis.get('modified_files', [])
        if modified:
            summary_parts.append("**Modified Files:**")
            for file in modified:
                summary_parts.append(
                    f"- {file.get('path', 'unknown')}: {file.get('change_type', 'modified')}"
                )
            summary_parts.append("")
        
        # Breaking changes
        breaking = analysis.get('breaking_changes', [])
        if breaking:
            summary_parts.append("**⚠️ Breaking Changes:**")
            for change in breaking:
                summary_parts.append(f"- {change}")
            summary_parts.append("")
        
        # Risk flags
        risks = analysis.get('risk_flags', [])
        if risks:
            summary_parts.append("**Risk Flags:**")
            for risk in risks:
                severity = risk.get('severity', 'unknown')
                desc = risk.get('description', 'No description')
                summary_parts.append(f"- [{severity.upper()}] {desc}")
            summary_parts.append("")
        
        return "\n".join(summary_parts)
    
    def identify_affected_docs(self, analysis: Dict) -> List[str]:
        """
        Identify which documentation needs to be updated
        
        Args:
            analysis: PR analysis result
            
        Returns:
            List of documentation sections to update
        """
        return analysis.get('affected_documentation', [])


# Example usage
if __name__ == "__main__":
    agent = ChangeAgent()
    
    # Test PR analysis
    result = agent.analyze_pr(
        pr_number=234,
        repo_url="https://github.com/example/repo"
    )
    
    print(json.dumps(result, indent=2))
    
    # Test change summary
    summary = agent.generate_change_summary(agent._get_sample_diff())
    print(f"\nChange Summary:\n{summary}")
