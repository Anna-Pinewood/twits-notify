REDDIT_ANALYSIS_PROMPT = '''You are an expert at analyzing Reddit discussions and extracting key insights.
Analyze the following Reddit post and its comments to extract tags and provide a concise discussion summary.
Focus on the main themes, topics, opinions, and any significant points raised in the discussion.

Post Content:
{post_content}

Please provide your analysis in the following JSON format:
{{
    "tags": ["tag1", "tag2", "tag3"], // 3-7 relevant topic tags
    "discussion_summary": "concise summary of the discussion", // 2-3 sentences
}}

Requirements for the analysis:
- Tags should be specific but not too narrow
- Discussion summary should capture key points and overall sentiment
- All text fields must be in English
'''
