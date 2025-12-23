from bs4 import BeautifulSoup

def inspect():
    with open('clien_article_ua.html', 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check comment view container
    cv = soup.find(class_='comment_view')
    if not cv:
        print("No .comment_view found")
    else:
        print(f"Found .comment_view with {len(cv.find_all(recursive=False))} direct children")
        
        # Analyze potential comment rows
        # Look for elements that recur
        children = cv.find_all(recursive=False)
        for i, child in enumerate(children[:5]):
            print(f"Child {i}: Name={child.name}, Classes={child.get('class')}, ID={child.get('id')}")
            
    # Check for specific classes found in grep
    heads = soup.find_all(class_='comment_head')
    print(f"Found {len(heads)} .comment_head elements")
    
    print(f"Found {len(soup.find_all(class_='post_comment'))} .post_comment elements")
    print(f"Found {len(soup.find_all(class_='re_comment'))} .re_comment elements")
    
    msgs = soup.find_all(class_='comment_msg')
    print(f"Found {len(msgs)} .comment_msg elements")

    if msgs:
        print(f"Parent of first msg: {msgs[0].parent.name} classes={msgs[0].parent.get('class')}")
        print(f"Grandparent of first msg: {msgs[0].parent.parent.name} classes={msgs[0].parent.parent.get('class')}")


    # Check for data-role
    rows = soup.find_all(attrs={'data-role': 'comment-row'})
    print(f"Found {len(rows)} elements with data-role='comment-row'")
    
    if rows:
        print("Inspection of first row:")
        print(rows[0].prettify()[:500])

if __name__ == '__main__':
    inspect()
