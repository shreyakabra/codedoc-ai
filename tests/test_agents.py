"""
Tests for CodeDoc AI Agents
"""
import pytest
from src.agents.qa_agent import QAAgent
from src.agents.summarizer import SummarizerAgent
from src.agents.parser import ParserAgent


class TestQAAgent:
    """Tests for QA Agent"""
    
    def test_answer_question(self):
        """Test answering a simple question"""
        agent = QAAgent()
        result = agent.answer_question("What is this codebase about?")
        
        assert result is not None
        assert result.answer is not None
        assert result.confidence >= 0.0
        assert result.latency_ms > 0
    
    def test_conversation_history(self):
        """Test conversation history is maintained"""
        agent = QAAgent()
        
        # Ask first question
        agent.answer_question("How does authentication work?")
        
        # Check history
        assert len(agent.conversation_history) > 0
        
        # Reset and verify
        agent.reset_conversation()
        assert len(agent.conversation_history) == 0


class TestSummarizerAgent:
    """Tests for Summarizer Agent"""
    
    def test_short_summary(self):
        """Test short summary generation"""
        agent = SummarizerAgent()
        chunks = [
            {
                "text": "def hello(): pass",
                "metadata": {"file_path": "test.py"}
            }
        ]
        
        summary = agent.generate_short_summary(chunks)
        assert len(summary) > 0
        assert len(summary) < 500  # Should be short
    
    def test_onboarding_guide(self):
        """Test onboarding guide generation"""
        agent = SummarizerAgent()
        guide = agent.generate_onboarding_guide("https://github.com/test/repo")
        
        assert "onboarding" in guide.lower() or "#" in guide
        assert len(guide) > 100


class TestParserAgent:
    """Tests for Parser Agent"""
    
    def test_parse_python_file(self):
        """Test parsing Python code"""
        agent = ParserAgent()
        code = """
def hello_world():
    '''Say hello'''
    print("Hello, World!")
"""
        
        result = agent.parse_file("test.py", content=code)
        
        assert result is not None
        assert result.get("language") == "python"
        # Note: Actual parsing requires Groq API
    
    def test_detect_language(self):
        """Test language detection"""
        agent = ParserAgent()
        
        assert agent._detect_language("test.py") == "python"
        assert agent._detect_language("test.js") == "javascript"
        assert agent._detect_language("test.java") == "java"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
