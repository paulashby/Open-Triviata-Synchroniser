import sys
import argparse
from helpers import new_token, update_trivia_categories, next_category, level_counts, process_category

def main():
    parser = argparse.ArgumentParser(description="-t Use existing token if available - API will not return questions already provided within the last 6 hours")
    parser.add_argument('-t', action='store_true')
    args = parser.parse_args()

    if not args.t:
        # get new token to ensure api returns unique questions (going forward - they're only unique to the new token)
        new_token()

    # Make sure we're in sync with Open Trivia
    update_trivia_categories()

    # Start with the next incomplete category
    category = next_category()

    while category:

        category_id = category['id']

        # Get number of questions already processed for each difficulty level
        already_done = level_counts(category_id)

        to_do_list = {
            'category': category_id,
            'total': category['total_question_count'],
            'levels': {}
        }

        for level, done in already_done.items():
            # Check for incomplete difficulty levels
            available_questions = category[f"total_{level}_question_count"]

            if done < available_questions:
                # There are more questions to process for this level - place in to_do_list
                to_do_list['levels'][level] = available_questions

        process_category(to_do_list)

        category = next_category(category_id + 1)

    print("SUCCESS: all questions have been processed :)")
    sys.exit(0)

if __name__ == "__main__":
    main()