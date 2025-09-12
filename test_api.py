"""Test script for API endpoints."""

import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test data
SAMPLE_TOPIC = {
    "title": "Hệ thống nhận diện đối tượng thời gian thực sử dụng Deep Learning",
    "description": "Xây dựng ứng dụng nhận diện và theo dõi đối tượng trong video thời gian thực sử dụng các mô hình deep learning hiện đại",
    "objectives": "Nghiên cứu và triển khai thuật toán deep learning cho việc nhận diện đối tượng với độ chính xác cao",
    "methodology": "Sử dụng YOLO hoặc R-CNN, training trên dataset tùy chỉnh, tối ưu hóa cho real-time processing",
    "expected_outcomes": "Ứng dụng demo có thể nhận diện đối tượng với độ chính xác > 85% và xử lý real-time",
    "requirements": "Kiến thức về deep learning, Python, OpenCV, và GPU computing",
    "supervisor_id": 1,
    "semester_id": 1,
    "category_id": 1,
    "max_students": 2
}

async def test_health_check():
    """Test health check endpoint."""
    print("🏥 Testing health check...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("-" * 50)

async def test_system_stats():
    """Test system statistics endpoint."""
    print("📊 Testing system stats...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/system/stats")
        
        if response.status_code == 200:
            print("✅ System stats retrieved")
            stats = response.json()
            print(f"   Main agent stats: {stats.get('main_agent', {})}")
            print(f"   ChromaDB info: {stats.get('chroma_collection', {})}")
        else:
            print(f"❌ System stats failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("-" * 50)

async def test_trending_suggestions():
    """Test trending suggestions endpoint."""
    print("💡 Testing trending suggestions...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {
            "semester_id": 1,
            "category_preference": "Artificial Intelligence",
            "keywords": ["AI", "machine learning"],
            "student_level": "undergraduate"
        }
        
        response = await client.get(f"{API_BASE}/topics/suggestions", params=params)
        
        if response.status_code == 200:
            print("✅ Trending suggestions retrieved")
            suggestions = response.json()
            print(f"   Number of suggestions: {len(suggestions.get('suggestions', []))}")
            print(f"   Trending areas: {suggestions.get('trending_areas', [])}")
            
            # Show first suggestion
            if suggestions.get('suggestions'):
                first_suggestion = suggestions['suggestions'][0]
                print(f"   First suggestion: {first_suggestion.get('title', 'N/A')}")
        else:
            print(f"❌ Trending suggestions failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("-" * 50)

async def test_duplicate_check():
    """Test duplicate check endpoint."""
    print("🔍 Testing duplicate check...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE}/topics/check-duplicates",
            json=SAMPLE_TOPIC
        )
        
        if response.status_code == 200:
            print("✅ Duplicate check completed")
            result = response.json()
            print(f"   Status: {result.get('status')}")
            print(f"   Similarity score: {result.get('similarity_score', 0):.2%}")
            print(f"   Similar topics found: {len(result.get('similar_topics', []))}")
            print(f"   Message: {result.get('message', 'N/A')}")
        else:
            print(f"❌ Duplicate check failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("-" * 50)

async def test_topic_creation_simple():
    """Test simple topic creation."""
    print("📝 Testing simple topic creation...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Modify title to avoid conflicts
        test_topic = SAMPLE_TOPIC.copy()
        test_topic["title"] = f"[TEST] {test_topic['title']}"
        
        response = await client.post(
            f"{API_BASE}/topics/create-simple",
            json=test_topic
        )
        
        if response.status_code == 200:
            print("✅ Simple topic creation successful")
            topic = response.json()
            print(f"   Created topic ID: {topic.get('id')}")
            print(f"   Title: {topic.get('title')}")
            return topic.get('id')
        else:
            print(f"❌ Simple topic creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    
    print("-" * 50)

async def test_topic_submission_with_ai():
    """Test full AI topic submission."""
    print("🤖 Testing AI-powered topic submission...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Modify title to avoid conflicts
        test_topic = SAMPLE_TOPIC.copy()
        test_topic["title"] = f"[AI-TEST] {test_topic['title']}"
        
        params = {
            "check_duplicates": True,
            "get_suggestions": False,  # Skip suggestions for faster testing
            "auto_modify": True
        }
        
        response = await client.post(
            f"{API_BASE}/topics/submit",
            json=test_topic,
            params=params
        )
        
        if response.status_code == 200:
            print("✅ AI topic submission successful")
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Topic ID: {result.get('topic_id')}")
            print(f"   Processing time: {result.get('processing_time')}s")
            print(f"   Messages: {result.get('messages', [])}")
            
            # Show duplicate check result if available
            if result.get('duplicate_check'):
                dup_result = result['duplicate_check']
                print(f"   Duplicate status: {dup_result.get('status')}")
                print(f"   Similarity: {dup_result.get('similarity_score', 0):.2%}")
            
            return result.get('topic_id')
        else:
            print(f"❌ AI topic submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    
    print("-" * 50)

async def test_get_topic(topic_id: int):
    """Test getting topic by ID."""
    if not topic_id:
        print("⏭️  Skipping get topic test (no topic ID)")
        return
    
    print(f"📖 Testing get topic by ID: {topic_id}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/topics/{topic_id}")
        
        if response.status_code == 200:
            print("✅ Get topic successful")
            topic = response.json()
            print(f"   Title: {topic.get('title')}")
            print(f"   Created: {topic.get('created_at')}")
        else:
            print(f"❌ Get topic failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("-" * 50)

async def test_search_topics():
    """Test topic search."""
    print("🔎 Testing topic search...")
    
    async with httpx.AsyncClient() as client:
        params = {
            "keywords": ["deep learning", "AI"],
            "semester_id": 1
        }
        
        response = await client.get(f"{API_BASE}/topics/search", params=params)
        
        if response.status_code == 200:
            print("✅ Topic search successful")
            topics = response.json()
            print(f"   Found {len(topics)} topics")
            
            for topic in topics[:3]:  # Show first 3
                print(f"   - {topic.get('title', 'N/A')}")
        else:
            print(f"❌ Topic search failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("-" * 50)

async def test_approved_topics():
    """Test getting approved topics."""
    print("✅ Testing approved topics...")
    
    async with httpx.AsyncClient() as client:
        params = {
            "semester_id": 1,
            "limit": 50
        }
        
        response = await client.get(f"{API_BASE}/topics/approved", params=params)
        
        if response.status_code == 200:
            print("✅ Approved topics retrieved")
            topics = response.json()
            print(f"   Found {len(topics)} approved topics")
            
            for topic in topics[:3]:  # Show first 3
                print(f"   - {topic.get('title', 'N/A')} (Approved: {topic.get('is_approved', False)})")
        else:
            print(f"❌ Approved topics failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("-" * 50)

async def main():
    """Run all tests."""
    print("🧪 Starting API tests for AI Agent Topic Submission System")
    print("=" * 60)
    
    try:
        # Basic tests
        await test_health_check()
        await test_system_stats()
        
        # AI functionality tests
        await test_trending_suggestions()
        await test_duplicate_check()
        
        # Topic creation tests
        simple_topic_id = await test_topic_creation_simple()
        ai_topic_id = await test_topic_submission_with_ai()
        
        # Topic retrieval tests
        await test_get_topic(simple_topic_id or ai_topic_id)
        await test_search_topics()
        await test_approved_topics()
        
        print("🎉 All tests completed!")
        
    except Exception as e:
        print(f"💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("📋 Note: Make sure the server is running on http://localhost:8000")
    print("   Start server with: python run_server.py")
    print()
    
    asyncio.run(main())
