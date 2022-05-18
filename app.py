import sys
from helpers import next_category
def main():

    QUERY_MAX = 50

    # Make sure we're working on the latest category
    category = next_category()

    if not category:
        print("SUCCESS: all questions have been processed :)")
        sys.exit(0)

    """
    category be all like:

    {'id': 9,
      'total_easy_question_count': 116,
      'total_hard_question_count': 59,
      'total_medium_question_count': 123,
      'total_question_count': 298
    }
    
    check
      - which difficulty levels (DLs) are lacking?
      - Redo those DLs

    num_full_calls = floor(current_category_info/QUERY_MAX)
    final_call_qty = current_category_info % QUERY_MAX
    """
    # else (our count is lower than total_question_count) either:
        # - new questions have been added
        # - something has gone wrong and we failed to complete the category on our previous session
        # In either case, we need to:
        
        # - check the counts for each level of difficulty (LOD), 
            # if we're short in all
                # - delete all questions for this category, remove it from the categories table and start again 
            # else 
                # - we're only short in some, delete all questions for each under-populated LOD and redo it - 
                # (will also need to delete from answers table AND category if we end up removing all)
                # - we are definitely short in at least one, since our category question count is lower than total_question_count



if __name__ == "__main__":
    main()